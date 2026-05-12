import os
import random
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# Agregamos CallbackQueryHandler aquí abajo 👇
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- 1. DESPERTADOR PARA RENDER (FLASK) ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "🥭 Sistema MANGO - Activo"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- 2. LÓGICA DEL BOT ---
rondas = {}

async def mensaje_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    boton_join = InlineKeyboardButton("UNIRME! 🎤", callback_data="unirme_click")
    reply_markup = InlineKeyboardMarkup([[boton_join]])

    await update.message.reply_text(
        "¡Bienvenidos al Ritmo A Go-Go! Presiona el botón para unirte:",
        reply_markup=reply_markup
    )

async def unirme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Esto quita el relojito de carga en el botón
    
    chat_id = query.message.chat.id
    user = query.from_user  # En botones usamos query.from_user
    
    if chat_id not in rondas:
        rondas[chat_id] = {"palabras": {}, "jugadores": [], "turno_idx": 0, "activa": False}
    
    if not any(j['id'] == user.id for j in rondas[chat_id]["jugadores"]):
        rondas[chat_id]["jugadores"].append({"id": user.id, "name": user.first_name})
        await query.message.reply_text(f"✅ **{user.first_name}** se unió al ritmo.")
    else:
        await query.message.reply_text(f"Ya estás adentro, {user.first_name}. ¡No te preocupes! jaksja")

async def iniciar_ritmo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id not in rondas or len(rondas[chat_id]["jugadores"]) < 2:
        await update.message.reply_text("Se necesitan mínimo 2 para poder jugar!")
        return

    tema = " ".join(context.args) if context.args else "lo que quieran"

    random.shuffle(rondas[chat_id]["jugadores"])
    rondas[chat_id]["activa"] = True
    rondas[chat_id]["palabras"] = {}
    rondas[chat_id]["turno_idx"] = 0
    
    primero = rondas[chat_id]["jugadores"][0]["name"]
    gif_start = "https://i.pinimg.com/originals/4f/67/6e/4f676ee6c7f543d92a2ea28109758120.gif"

    await update.message.reply_animation(
        animation = gif_start,
        caption = (
            f"✨ **¡RITMO... AGO-GO!** ✨\n"
            f"Diga usted nombres de... **{tema.upper()}**\n\n"
            f"Por ejemplo... ¡empieza **{primero}**! 🎤"
        ),
        parse_mode='Markdown'
    )

async def manejar_mensajes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if not update.message or not update.message.text:
        return

    texto_usuario = update.message.text.strip().lower()

    if chat_id not in rondas or not rondas[chat_id]["activa"]:
        return

    estado = rondas[chat_id]
    jugador_actual = estado["jugadores"][estado["turno_idx"]]

    if user_id != jugador_actual["id"]:
        return

    if texto_usuario in estado["palabras"]:
        quien_fue = estado["palabras"][texto_usuario]
        gif_end = "https://i.pinimg.com/originals/4f/67/6e/4f676ee6c7f543d92a2ea28109758120.gif"
        
        await update.message.reply_animation(
            animation = gif_end,
            caption = (
                f"💀 **¡TRAS! YOU LOSE BABE.** 💅\n\n"
                f"Esa ya la había dicho **{quien_fue}**.\n"
                f"Perdiste, {jugador_actual['name']} :("
            ),
            parse_mode='Markdown'
        )
        estado["activa"] = False
    else:
        estado["palabras"][texto_usuario] = jugador_actual["name"]
        estado["turno_idx"] = (estado["turno_idx"] + 1) % len(estado["jugadores"])
        
        proximo = estado["jugadores"][estado["turno_idx"]]["name"]
        await update.message.reply_text(f"✅ ¡Sigue! Turno de: **{proximo}**", parse_mode='Markdown')

if __name__ == '__main__':
    TOKEN = os.getenv("TOKEN_TELEGRAM")
    
    if not TOKEN:
        print("❌ Error: No se encontró el TOKEN_TELEGRAM")
    else:
        keep_alive()
        app = ApplicationBuilder().token(TOKEN).build()
        
        # --- LOS HANDLERS (AQUÍ ESTABA EL TRUCO) ---
        
        # 1. El comando /start ahora lanza el mensaje con botón
        app.add_handler(CommandHandler("start", mensaje_join))
        
        # 2. El oído para el botón (reemplaza al CommandHandler de "unirme")
        app.add_handler(CallbackQueryHandler(unirme, pattern="unirme_click"))
        
        # 3. El resto de comandos y mensajes
        app.add_handler(CommandHandler("ritmo", iniciar_ritmo))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_mensajes))
        
        print("Bot de ritmo corriendo... 🚀")
        app.run_polling()
