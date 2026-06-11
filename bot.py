"""Telegram chatbot with conversation memory, SOUL.md personality, and auth."""

import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from collections import defaultdict

from core.config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OLLAMA_URL,
    OLLAMA_BOT_MODEL, OLLAMA_MODEL, USER_NAME, load_soul, setup_logging
)
from core.notifier import is_authorized_chat
from core.cache import load_chat_history, save_chat_history, JobCache

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

# ─── Conversation memory (per-chat, persisted) ───
# Stores last N messages per chat_id
MAX_HISTORY = 20
chat_histories: dict[int, list[dict]] = load_chat_history()


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
        # Initialize key if not present
        if chat_id not in chat_histories:
            chat_histories[chat_id] = []

        # Add user message to history
        chat_histories[chat_id].append({"role": "user", "content": user_text})
        save_chat_history(chat_histories)

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
        save_chat_history(chat_histories)

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


async def handle_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /yes <job_id> to register positive feedback."""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    if not is_authorized_chat(chat_id):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /yes <job_id>\nExample: /yes abcd12")
        return

    job_id = context.args[0]
    cache = JobCache()
    if cache.set_feedback(job_id, "like"):
        key = cache.find_key_by_short_id(job_id)
        job_info = cache._cache[key]
        title = job_info.get("title", "this role")
        company = job_info.get("company", "")
        company_str = f" @ {company}" if company else ""
        await update.message.reply_text(f"🟢 <b>Feedback Saved:</b> Liked \"{title}{company_str}\". Local LLM will prioritize similar jobs in future runs.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ Could not find a job matching ID: <code>{job_id}</code>", parse_mode="HTML")


async def handle_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /no <job_id> to register negative feedback."""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    if not is_authorized_chat(chat_id):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /no <job_id>\nExample: /no abcd12")
        return

    job_id = context.args[0]
    cache = JobCache()
    if cache.set_feedback(job_id, "dislike"):
        key = cache.find_key_by_short_id(job_id)
        job_info = cache._cache[key]
        title = job_info.get("title", "this role")
        company = job_info.get("company", "")
        company_str = f" @ {company}" if company else ""
        await update.message.reply_text(f"🔴 <b>Feedback Saved:</b> Disliked \"{title}{company_str}\". Local LLM will avoid similar jobs in future runs.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ Could not find a job matching ID: <code>{job_id}</code>", parse_mode="HTML")


async def handle_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /apply <job_id> to record application status."""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    if not is_authorized_chat(chat_id):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /apply <job_id>\nExample: /apply abcd12")
        return

    job_id = context.args[0]
    cache = JobCache()
    if cache.set_state(job_id, "applied"):
        key = cache.find_key_by_short_id(job_id)
        job_info = cache._cache[key]
        title = job_info.get("title", "this role")
        company = job_info.get("company", "")
        company_str = f" @ {company}" if company else ""
        await update.message.reply_text(f"💼 <b>Application Logged:</b> Marked \"{title}{company_str}\" as <b>applied</b>.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ Could not find a job matching ID: <code>{job_id}</code>", parse_mode="HTML")


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status to view system state and applied jobs."""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    if not is_authorized_chat(chat_id):
        return

    cache = JobCache()
    applied = cache.get_applied_jobs()
    exemplars = cache.get_feedback_exemplars()
    
    likes = sum(1 for e in exemplars if e["feedback"] == "like")
    dislikes = sum(1 for e in exemplars if e["feedback"] == "dislike")

    applied_list_str = ""
    if applied:
        applied_list_str = "\n\n💼 <b>Recent Applications:</b>"
        for idx, job in enumerate(applied[-5:], 1):
            date_str = job["date"][:10] if job["date"] else "N/A"
            applied_list_str += f"\n {idx}. {job['title']} @ {job['company']} (Logged: {date_str})"
    else:
        applied_list_str = "\n\n💼 No logged applications yet. Mark matches with <code>/apply &lt;job_id&gt;</code>."

    status_msg = (
        f"🖥️ <b>JobScout-Lite Status</b>\n"
        f"🤖 Chat Model: <code>{OLLAMA_BOT_MODEL}</code>\n"
        f"🧠 Match Model: <code>{OLLAMA_MODEL}</code>\n"
        f"📂 Cache size: <b>{cache.size}</b> jobs\n"
        f"📝 Feedback loop active: 🟢 {likes} likes | 🔴 {dislikes} dislikes"
        f"{applied_list_str}"
    )
    await update.message.reply_text(status_msg, parse_mode="HTML")


if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        exit(1)

    logger.info("Starting AI Assistant Bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Register commands
    app.add_handler(CommandHandler("yes", handle_yes))
    app.add_handler(CommandHandler("no", handle_no))
    app.add_handler(CommandHandler("apply", handle_apply))
    app.add_handler(CommandHandler("status", handle_status))
    
    # Register message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info(f"Bot is online! Model: {OLLAMA_BOT_MODEL}")
    app.run_polling()