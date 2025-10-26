# API bot "8240420240:AAHln5eJ7G1tThAkbwXJHCEVYaK4afG4R5g"
import pandas as pd
import matplotlib.pyplot as plt
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

CHOOSING, ADD_EVENT = range(2)
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Benvenuto nel bot Masaniello!\nPer istruzioni invia /help."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**Comandi disponibili:**\n"
        "/start - Benvenuto\n"
        "/help - Mostra istruzioni\n"
        "/setup - Nuova serie Masaniello\n"
        "/cancel - Interrompi sessione\n"
        "/restart - Reset sessione e riparti\n\n"
        "Durante la serie, invia 'v' (vinto) o 'p' (perso) per ogni evento.\n"
        "Al termine riceverai solo i grafici automatici!"
    )

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Capitale iniziale (€):")
    user_states[update.effective_user.id] = {'step': 'capital'}
    return CHOOSING

async def scegli_parametro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    input_text = update.message.text
    stato = user_states.get(uid, {})
    step = stato.get('step')

    try:
        if step == 'capital':
            stato['capital'] = float(input_text)
            stato['step'] = 'quota'
            await update.message.reply_text("Quota media (es. 1.5):")
        elif step == 'quota':
            stato['quota'] = float(input_text)
            stato['step'] = 'eventi'
            await update.message.reply_text("Numero eventi nella serie:")
        elif step == 'eventi':
            stato['num_eventi'] = int(input_text)
            stato['step'] = 'errori'
            await update.message.reply_text("Numero errori ammessi:")
        elif step == 'errori':
            stato['errori'] = int(input_text)
            stato['step'] = 'evento'
            stato['corrente'] = 1
            stato['cassa'] = stato['capital']
            stato['vittorie'] = 0
            stato['perdite'] = 0
            stato['storico'] = []
            await update.message.reply_text(
                f"Inizia la serie!\nInvia 'v' per vinto, 'p' per perso (Evento 1)."
            )
            user_states[uid] = stato
            return ADD_EVENT
        user_states[uid] = stato
        return CHOOSING
    except Exception:
        await update.message.reply_text("Valore non valido. Riprova.")
        return CHOOSING

async def registra_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    stato = user_states.get(uid, {})
    quota = stato.get('quota')
    evento = stato.get('corrente')
    num_eventi = stato.get('num_eventi')
    errori_max = stato.get('errori')
    vinto = update.message.text.lower().strip() == 'v'

    if evento == 1:
        puntata = stato['cassa'] * 0.05
    else:
        fattore_rischio = (stato['perdite'] + 1) / evento
        puntata = stato['cassa'] * (0.05 + 0.02 * fattore_rischio)

    if vinto:
        vincita = puntata * (quota - 1)
        stato['cassa'] += vincita
        stato['vittorie'] += 1
        esito = '✅'
    else:
        stato['cassa'] -= puntata
        stato['perdite'] += 1
        esito = '❌'

    stato['storico'].append({
        'Evento': evento,
        'Esito': esito,
        'Puntata (€)': round(puntata,2),
        'Cassa dopo evento (€)': round(stato['cassa'],2),
        'Vinte': stato['vittorie'],
        'Perse': stato['perdite']
    })

    evento += 1
    stato['corrente'] = evento

    # -- FINE SERIE --
    if stato['perdite'] > errori_max or evento > num_eventi:
        df = pd.DataFrame(stato['storico'])
        if not df.empty and len(df) > 1:
            image_name1 = f"masaniello_{uid}_cassa.png"
            image_name2 = f"masaniello_{uid}_puntata.png"
            # CASSA
            plt.figure(figsize=(8,5))
            plt.plot(df['Evento'], df['Cassa dopo evento (€)'], marker='o', linestyle='-', label='Cassa (€)')
            plt.title('Andamento Cassa Masaniello')
            plt.xlabel('Evento')
            plt.ylabel('Cassa (€)')
            plt.grid()
            plt.legend()
            plt.tight_layout()
            plt.savefig(image_name1, format="png")
            plt.close()
            # PUNTATA
            plt.figure(figsize=(8,5))
            plt.plot(df['Evento'], df['Puntata (€)'], marker='s', color='orange', linestyle='-', label='Puntata (€)')
            plt.title('Puntata consigliata Masaniello')
            plt.xlabel('Evento')
            plt.ylabel('Puntata (€)')
            plt.grid()
            plt.legend()
            plt.tight_layout()
            plt.savefig(image_name2, format="png")
            plt.close()
            await update.message.reply_text(
                f"Serie terminata 🏁\nCassa finale: {round(stato['cassa'],2)} €\n\n"
                "La serie impostata è terminata.\nUsa /setup per iniziare una nuova serie oppure /help per la lista comandi."
            )
            # Invia immagini solo se PNG > 1000 byte e cancella dopo invio! USA file binario
            for path, didascalia in [(image_name1, "Andamento cassa"), (image_name2, "Andamento puntata")]:
                if os.path.exists(path) and os.path.getsize(path) > 1000:
                    try:
                        with open(path, 'rb') as img:
                            await update.message.reply_photo(photo=img, caption=didascalia)
                        os.remove(path)
                    except Exception as e:
                        await update.message.reply_text(f"Immagine non inviata: {str(e)}")
                else:
                    await update.message.reply_text("Grafico non valido (meno di 2 dati, file corrotto o troppo piccolo).")
        else:
            await update.message.reply_text(
                f"Serie terminata 🏁\nCassa finale: {round(stato['cassa'],2)} €\n\n"
                "Non abbastanza dati per generare grafici validi.\nUsa /setup per una nuova serie."
            )
        user_states.pop(uid)
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"Evento {evento}/{num_eventi} - Cassa {round(stato['cassa'],2)} €\n"
            f"Puntata consigliata: {round(puntata,2)} €\n"
            "Invia 'v' (vinto) o 'p' (perso) per il prossimo evento."
        )
        user_states[uid] = stato
        return ADD_EVENT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states.pop(update.effective_user.id, None)
    await update.message.reply_text("Sessione Masaniello annullata.")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "Sessione corrente annullata ✅\nUsa /setup per iniziare una nuova serie."
    )
    return ConversationHandler.END

if __name__ == '__main__':
    TOKEN = '8240420240:AAHln5eJ7G1tThAkbwXJHCEVYaK4afG4R5g'  # <-- Inserisci qui il tuo token Telegram
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('setup', setup)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, scegli_parametro)],
            ADD_EVENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, registra_evento)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('restart', restart),
            CommandHandler('help', help_command)
        ]
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('cancel', cancel))
    app.add_handler(CommandHandler('restart', restart))

    print("Bot avviato…")
    app.run_polling()
