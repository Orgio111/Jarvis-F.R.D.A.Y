"""
JARVIS Telegram Bot
────────────────────
All messages are forwarded to the JARVIS API. The bot keeps a per-chat
session ID so memory is scoped correctly.

Commands:
  /start        – welcome message
  /help         – list commands
  /memory <q>   – semantic memory search
  /skills       – list stored skills
  /run <goal>   – trigger agent loop
  /clear        – clear current session

Environment variables required:
  TELEGRAM_BOT_TOKEN   – BotFather token
  JARVIS_URL           – gateway URL (default http://localhost:8000)
  JARVIS_API_KEY       – optional API key
"""
from __future__ import annotations

import asyncio
import logging
import os
from uuid import uuid4

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.client import BotClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_client = BotClient(
    base_url=os.getenv("JARVIS_URL", "http://localhost:8000"),
    api_key=os.getenv("JARVIS_API_KEY", ""),
)

# session_id per chat_id so memory is scoped correctly
_sessions: dict[int, str] = {}


def _session(chat_id: int) -> str:
    if chat_id not in _sessions:
        _sessions[chat_id] = f"tg_{uuid4().hex[:12]}"
    return _sessions[chat_id]


# ─── Handlers ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *JARVIS online.*\n\nJust send me a message to chat, or use /help for commands.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*Commands*\n"
        "/memory \\<query\\> — search long\\-term memory\n"
        "/skills — list stored skills\n"
        "/run \\<goal\\> — launch agent loop\n"
        "/clear — start a fresh session\n\n"
        "_Or just chat normally_ 💬"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_memory(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(ctx.args or [])
    if not query:
        await update.message.reply_text("Usage: /memory <search query>")
        return
    await update.message.chat.send_action(ChatAction.TYPING)
    results = await _client.memory_search(query, top_k=5)
    if not results:
        await update.message.reply_text("No matching memories found.")
        return
    lines = [f"• ({r.get('type', '?')}) {r.get('content', '')[:150]}" for r in results[:5]]
    await update.message.reply_text("🧠 *Memory results:*\n" + "\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_skills(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action(ChatAction.TYPING)
    skills = await _client.skills_list()
    if not skills:
        await update.message.reply_text("No skills stored yet.")
        return
    lines = [f"• `{s['skillId']}` — {s['name']} (quality: {s.get('qualityScore', 0):.2f})" for s in skills[:10]]
    await update.message.reply_text("🛠 *Skills:*\n" + "\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_run(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    goal = " ".join(ctx.args or [])
    if not goal:
        await update.message.reply_text("Usage: /run <your goal>")
        return
    await update.message.chat.send_action(ChatAction.TYPING)
    msg = await update.message.reply_text("⚙️ Agent running…")
    user_id = f"tg_{update.effective_user.id}"
    answer = await _client.run_agent(goal, user_id=user_id)
    await msg.edit_text(f"✅ *Done*\n\n{answer[:3500]}", parse_mode=ParseMode.MARKDOWN)


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _sessions.pop(chat_id, None)
    await update.message.reply_text("🗑 Session cleared — starting fresh.")


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    if not text:
        return

    chat_id = update.effective_chat.id
    user_id = f"tg_{update.effective_user.id}"
    session_id = _session(chat_id)

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        reply = await _client.chat(text, session_id=session_id, user_id=user_id)
    except Exception as exc:
        reply = f"⚠️ Error: {exc}"

    # Telegram has a 4096-char limit per message
    for chunk in _chunk(reply or "…", 4000):
        await update.message.reply_text(chunk)


def _chunk(text: str, size: int):
    for i in range(0, max(len(text), 1), size):
        yield text[i: i + size]


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")

    app = (
        Application.builder()
        .token(token)
        .build()
    )

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("run",    cmd_run))
    app.add_handler(CommandHandler("clear",  cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("JARVIS Telegram bot starting…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
