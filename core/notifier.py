"""
Telegram notification module.
Handles sending messages, splitting long content, and formatting job results.
"""

import asyncio
from telegram import Bot
from core.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, setup_logging
from core.scorer import get_match_emoji, get_match_label

logger = setup_logging("notifier")


async def send_telegram(message: str):
    """Send a message to the configured Telegram chat. Handles chunking."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials not configured. Skipping notification.")
        return

    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
        for chunk in chunks:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=chunk,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


def format_job_message(job: dict, rank: int) -> str:
    """Format a single job result for Telegram."""
    match_tier = job.get("match_tier", "SKIP")
    emoji = get_match_emoji(match_tier)
    label = get_match_label(match_tier)
    reason = job.get("match_reason", "")
    
    pitch = job.get("tailored_pitch", "")
    pitch_section = ""
    if pitch:
        pitch_section = f"\n\n📝 <b>Personalized Application Pitch:</b>\n<code>{pitch}</code>"

    return (
        f"{emoji} <b>#{rank} — {label}</b>\n"
        f"💼 <b>{job['title']}</b>\n"
        f"🏢 {job.get('company', 'Unknown')}\n"
        f"📍 {job.get('location', 'Unknown')}\n"
        f"🌐 {job.get('source', 'Unknown')}\n"
        f"💡 {reason}\n"
        f"🔗 <a href='{job.get('apply_url', '#')}'>Apply Here</a>"
        f"{pitch_section}"
    )


def is_authorized_chat(chat_id: int | str) -> bool:
    """Check if a Telegram chat ID is authorized to use the bot."""
    if not TELEGRAM_CHAT_ID:
        return False
    return str(chat_id) == str(TELEGRAM_CHAT_ID)
