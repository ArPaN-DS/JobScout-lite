import httpx  # Faster and better for Async bots
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

import os
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = os.getenv("OLLAMA_BOT_MODEL", "qwen3:fast")  # The bot uses the faster model
USER_NAME = os.getenv("USER_NAME", "User")

SYSTEM_PROMPT = f"""You are {USER_NAME}'s private personal assistant.
Be concise, smart, and friendly. Always respond in the same language the user writes in."""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    print(f"User: {user_text}")
    
    status_msg = await update.message.reply_text("⏳ Thinking...")
    
    try:
        # Using httpx for better performance
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(OLLAMA_URL, json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ],
                "stream": False
            })
        
        reply = response.json()["message"]["content"]
        
        # Remove the "Thinking" message before sending the real answer
        await status_msg.delete()

        # Handle Telegram's 4096 character limit
        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                await update.message.reply_text(reply[i:i+4096])
        else:
            await update.message.reply_text(reply)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🤖 Starting AI Assistant Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"✅ Bot is online! Message your AI Assistant on Telegram.")
    app.run_polling()