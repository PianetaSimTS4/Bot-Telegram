import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import telegram.error

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Qui prende il token dalla variabile di ambiente
ADMIN_IDS = [684167003, 559764759, 1872215746]  # Sostituisci con gli ID degli amministratori

# File per memorizzare i messaggi
STORAGE_FILE = "messaggi.json"

# Carica messaggi salvati se esistono
if os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, "r") as f:
        posted_messages = json.load(f)
else:
    posted_messages = {}

# Funzione per salvare i messaggi su file
def salva_messaggi():
    with open(STORAGE_FILE, "w") as f:
        json.dump(posted_messages, f)

# Comando /post per inviare messaggi o immagini
async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Non sei autorizzato.")
        return

    if not context.args:
        await update.message.reply_text("📌 Usa: /post ID [testo] oppure allega una foto con /post ID nella didascalia.")
        return

    msg_id = context.args[0]
    content = " ".join(context.args[1:]) if len(context.args) > 1 else update.message.caption

    if update.message.photo:
        # Se è un'immagine
        photo = update.message.photo[-1].file_id
        msg = await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo,
            caption=content or "📷",
            parse_mode="HTML"
        )
        posted_messages[msg_id] = {
            "chat_id": update.effective_chat.id,
            "message_id": msg.message_id,
            "type": "photo",
            "media": photo
        }
    else:
        # Se è un testo
        if not content:
            await update.message.reply_text("❌ Nessun testo inserito.")
            return
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=content,
            parse_mode="HTML"
        )
        posted_messages[msg_id] = {
            "chat_id": update.effective_chat.id,
            "message_id": msg.message_id,
            "type": "text"
        }

    # Gestiamo il messaggio di conferma con un try-except
    try:
        await update.message.reply_text(f"✅ Messaggio pubblicato con ID {msg_id}.")
    except telegram.error.BadRequest:
        await update.message.reply_text("❌ Errore: il messaggio a cui rispondere non è stato trovato.")
    
    salva_messaggi()

# Comando /modifica per modificare messaggi
async def modifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Non sei autorizzato.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("📌 Usa: /modifica ID nuovo contenuto")
        return

    msg_id = context.args[0]
    new_text = " ".join(context.args[1:])

    if msg_id not in posted_messages:
        await update.message.reply_text("⚠️ Nessun messaggio trovato con questo ID.")
        return

    info = posted_messages[msg_id]

    try:
        if info["type"] == "text":
            # Modifica testo
            await context.bot.edit_message_text(
                chat_id=info["chat_id"],
                message_id=info["message_id"],
                text=new_text,
                parse_mode="HTML"
            )
        elif info["type"] == "photo":
            # Modifica didascalia immagine
            await context.bot.edit_message_caption(
                chat_id=info["chat_id"],
                message_id=info["message_id"],
                caption=new_text,
                parse_mode="HTML"
            )
        await update.message.reply_text(f"✅ Messaggio ID {msg_id} modificato.")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore nella modifica: {e}")

# Comando /lista per vedere tutti i messaggi
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Non sei autorizzato.")
        return

    if not posted_messages:
        await update.message.reply_text("📭 Nessun messaggio salvato.")
        return

    risposta = "📋 <b>Messaggi postati:</b>\n\n"
    for msg_id, info in posted_messages.items():
        tipo = "📝 Testo" if info["type"] == "text" else "🖼️ Immagine"
        preview = f"{tipo} (ID: <code>{msg_id}</code>)"
        risposta += f"{preview}\n"

    await update.message.reply_text(risposta, parse_mode="HTML")

# Gestione foto con /post nella didascalia
async def photo_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.caption:
        return
    parts = update.message.caption.strip().split()
    if parts[0] != "/post" or len(parts) < 2:
        return
    context.args = parts[1:]
    update.message.caption = " ".join(parts)
    await post(update, context)

# Avvia il bot
app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("post", post))
app.add_handler(CommandHandler("modifica", modifica))
app.add_handler(CommandHandler("lista", lista))
app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex("^/post"), photo_post))
app.run_polling()
