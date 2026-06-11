"""Telegram chatbot with conversation memory, SOUL.md personality, and auth."""

import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from collections import defaultdict

from core.config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OLLAMA_URL,
    OLLAMA_BOT_MODEL, USER_NAME, load_soul, setup_logging
)
from core.notifier import is_authorized_chat

logger = setup_logging("bot")

# ─── SOUL.md personality loading ─────────────────
soul_text = load_soul()
if soul_text:
    SYSTEM_PROMPT = soul_text
    logger.info("Loaded SOUL.md personality")
else:
    SYSTEM_PROMPT = (
        f"You are {USER_NAME}'s private personal assistant. "
        "Be concise, smart, and friendly. Always respond in the same language the user writes in."
    )
    logger.info("No SOUL.md found, using default personality")

# ─── Conversation memory (per-chat) ─────────────
# Stores last N messages per chat_id
MAX_HISTORY = 20
chat_histories: dict[int, list[dict]] = defaultdict(list)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming Telegram messages with auth, memory, and error handling."""
    if not update.message or not update.effective_chat:
        return
        
    chat_id = update.effective_chat.id

    # ── Authentication ──
    if not is_authorized_chat(chat_id):
        logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
        await update.message.reply_text("⛔ Unauthorized. This bot is private.")
        return

    user_text = update.message.text
    logger.info(f"User: {user_text[:100]}")

    status_msg = await update.message.reply_text("⏳ Thinking...")

    try:
        # Add user message to history
        chat_histories[chat_id].append({"role": "user", "content": user_text})

        # Trim history to last MAX_HISTORY messages
        if len(chat_histories[chat_id]) > MAX_HISTORY:
            chat_histories[chat_id] = chat_histories[chat_id][-MAX_HISTORY:]

        # Build message list: system prompt + history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(chat_histories[chat_id])

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(OLLAMA_URL, json={
                "model": OLLAMA_BOT_MODEL,
                "messages": messages,
                "stream": False,
                "keep_alive": "60s",  # Unloads model from VRAM if user goes idle for 60 seconds
                "options": {
                    "num_ctx": 2048,  # Optimized context window saves VRAM
                }
            })

        if response.status_code != 200:
            raise Exception(f"Ollama returned status {response.status_code}")

        data = response.json()
        reply = data.get("message", {}).get("content", "")

        if not reply:
            raise Exception("Empty response from Ollama")

        # Strip thinking tokens if present
        import re
        reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()

        # Add assistant response to history
        chat_histories[chat_id].append({"role": "assistant", "content": reply})

        # Remove the "Thinking" message
        try:
            await status_msg.delete()
        except Exception:
            pass  # Message may already be deleted

        # Handle Telegram's 4096 character limit
        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                await update.message.reply_text(reply[i:i+4096])
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        try:
            await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")
        except Exception:
            await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        exit(1)

    logger.info("Starting AI Assistant Bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info(f"Bot is online! Model: {OLLAMA_BOT_MODEL}")
    app.run_polling()