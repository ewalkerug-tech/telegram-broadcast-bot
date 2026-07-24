import os
import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext

# 1. Environment Configurations
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
IB_LINK = os.getenv("EXNESS_IB_LINK")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") # Provided automatically by Render

# Initialize Core Telegram Objects
tg_bot = Bot(token=BOT_TOKEN)
ptb_app = Application.builder().token(BOT_TOKEN).build()

# 2. Telegram Logic: What happens when a user clicks /start
async def start_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    # This automatically builds the tracked link with their unique Telegram ID
    personalized_link = f"{IB_LINK}?sub1={user_id}"
    
    keyboard = [[InlineKeyboardButton("🔗 Register Exness Account", url=personalized_link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=f"Welcome {update.effective_user.first_name}!\n\n"
             "Click the button below to sign up. Once your account is opened, "
             "our system will automatically verify your ID and send your premium channel invite link here.",
        reply_markup=reply_markup
    )

ptb_app.add_handler(CommandHandler("start", start_command))

# 3. Lifespan Management: Tells Telegram where to send updates on app startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tell Telegram to send user messages directly to our Render URL endpoint
    await tg_bot.set_webhook(url=f"{RENDER_URL}/telegram-webhook")
    async with ptb_app:
        await ptb_app.start()
        yield
        await ptb_app.stop()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"status": "The gating server is live and running."}

# 4. Route A: Listens for Telegram User Actions (/start, etc.)
@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    payload = await request.json()
    update = Update.de_json(payload, tg_bot)
    await ptb_app.process_update(update)
    return Response(status_code=200)

# 5. Route B: Listens for Exness Postback Signals
@app.post("/exness-webhook")
async def exness_webhook(request: Request):
    payload = await request.json() if await request.body() else dict(request.query_params)
    
    tg_id = payload.get("telegram_id")
    exness_id = payload.get("exness_id")
    
    if not tg_id or not exness_id:
        return Response(content="Invalid Payload Parameters", status_code=400)
    
    try:
        # Generate a single-use channel ticket
        invite = await tg_bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        
        # Message the specific user directly with their access link
        await tg_bot.send_message(
            chat_id=tg_id,
            text=f"✅ Account Verified! Exness ID: {exness_id}\n\nHere is your private channel link: {invite.invite_link}"
        )
        return {"status": "success"}
    except Exception as e:
        print(f"Error handling invite: {e}")
        return Response(content=str(e), status_code=500)

