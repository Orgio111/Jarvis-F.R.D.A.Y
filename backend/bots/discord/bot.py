"""
JARVIS Discord Bot
────────────────────
Slash commands + natural language chat via the JARVIS backend API.

Slash commands:
  /chat <message>       – chat with JARVIS (private reply)
  /memory <query>       – semantic memory search
  /skills               – list stored skills
  /run <goal>           – agent loop
  /clear                – clear your session

Natural language: mention the bot (@JARVIS) in any channel.

Environment variables required:
  DISCORD_BOT_TOKEN    – Discord developer portal token
  DISCORD_GUILD_ID     – optional guild ID for instant slash command sync
  JARVIS_URL           – gateway URL (default http://localhost:8000)
  JARVIS_API_KEY       – optional API key
"""
from __future__ import annotations

import logging
import os
from uuid import uuid4

import discord
from discord import app_commands
from discord.ext import commands

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.client import BotClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_client_api = BotClient(
    base_url=os.getenv("JARVIS_URL", "http://localhost:8000"),
    api_key=os.getenv("JARVIS_API_KEY", ""),
)
_sessions: dict[int, str] = {}


def _session(user_id: int) -> str:
    if user_id not in _sessions:
        _sessions[user_id] = f"dc_{uuid4().hex[:12]}"
    return _sessions[user_id]


# ─── Bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
_GUILD = discord.Object(id=int(_GUILD_ID)) if _GUILD_ID else None


@bot.event
async def on_ready() -> None:
    logger.info(f"JARVIS Discord bot online as {bot.user}")
    if _GUILD:
        tree.copy_global_to(guild=_GUILD)
        await tree.sync(guild=_GUILD)
    else:
        await tree.sync()
    logger.info("Slash commands synced")


# ─── Slash commands ───────────────────────────────────────────────────────────

@tree.command(name="chat", description="Chat with JARVIS")
@app_commands.describe(message="Your message")
async def slash_chat(interaction: discord.Interaction, message: str) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    session_id = _session(interaction.user.id)
    user_id = f"dc_{interaction.user.id}"
    try:
        reply = await _client_api.chat(message, session_id=session_id, user_id=user_id)
    except Exception as exc:
        reply = f"⚠️ {exc}"
    for chunk in _chunk(reply or "…", 1990):
        await interaction.followup.send(chunk, ephemeral=True)


@tree.command(name="memory", description="Search long-term memory")
@app_commands.describe(query="What to search for")
async def slash_memory(interaction: discord.Interaction, query: str) -> None:
    await interaction.response.defer(ephemeral=True)
    results = await _client_api.memory_search(query, top_k=5)
    if not results:
        await interaction.followup.send("No matching memories.", ephemeral=True)
        return
    lines = [f"• ({r.get('type', '?')}) {r.get('content', '')[:200]}" for r in results]
    await interaction.followup.send("🧠 **Memory results:**\n" + "\n".join(lines), ephemeral=True)


@tree.command(name="skills", description="List stored JARVIS skills")
async def slash_skills(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    skills = await _client_api.skills_list()
    if not skills:
        await interaction.followup.send("No skills stored yet.", ephemeral=True)
        return
    lines = [f"• `{s['skillId']}` **{s['name']}** — quality: {s.get('qualityScore', 0):.2f}" for s in skills[:10]]
    await interaction.followup.send("🛠 **Skills:**\n" + "\n".join(lines), ephemeral=True)


@tree.command(name="run", description="Launch agent loop for a goal")
@app_commands.describe(goal="The goal you want JARVIS to accomplish")
async def slash_run(interaction: discord.Interaction, goal: str) -> None:
    await interaction.response.defer(thinking=True)
    user_id = f"dc_{interaction.user.id}"
    try:
        answer = await _client_api.run_agent(goal, user_id=user_id)
    except Exception as exc:
        answer = f"⚠️ {exc}"
    await interaction.followup.send(f"✅ **Done**\n\n{answer[:1900]}")


@tree.command(name="clear", description="Clear your JARVIS session")
async def slash_clear(interaction: discord.Interaction) -> None:
    _sessions.pop(interaction.user.id, None)
    await interaction.response.send_message("🗑 Session cleared.", ephemeral=True)


# ─── Mention handler (natural chat in channels) ───────────────────────────────

@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if bot.user not in message.mentions:
        await bot.process_commands(message)
        return

    text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not text:
        return

    async with message.channel.typing():
        session_id = _session(message.author.id)
        user_id = f"dc_{message.author.id}"
        try:
            reply = await _client_api.chat(text, session_id=session_id, user_id=user_id)
        except Exception as exc:
            reply = f"⚠️ {exc}"

    for chunk in _chunk(reply or "…", 1990):
        await message.reply(chunk)


def _chunk(text: str, size: int):
    for i in range(0, max(len(text), 1), size):
        yield text[i: i + size]


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN is not set")
    bot.run(token)


if __name__ == "__main__":
    main()
