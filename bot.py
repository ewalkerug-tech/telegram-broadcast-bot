import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Retrieve token and channel ID from environment variables for security
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Format: @your_channel_username or -100xxxxxxxxxx
PORT = int(os.getenv("PORT", 8080))

# Basic command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is running and ready to broadcast!")

# Command to broadcast a message to your channel
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast your message here")
        return
    
    text_to_send = " ".join(context.args)
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text_to_send)
        await update.message.reply_text("Message broadcasted successfully!")
    except Exception as e:
        await update.message.reply_text(f"Failed to send message: {e}")

# Web server health check endpoint for Render
async def handle_health(request):
    return web.Response(text="Bot is alive!")

async def main():
    # 1. Initialize Telegram Bot
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))

    # 2. Start Telegram Bot in polling mode
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # 3. Start Web Server for Render health checks
    app = web.Application()
    app.router.add_get('/', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())

