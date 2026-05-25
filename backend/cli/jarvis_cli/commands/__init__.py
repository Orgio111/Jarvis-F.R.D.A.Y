"""
JARVIS CLI Command Definitions.

Each command is a callable with a consistent interface:
    async def handler(client: JarvisClient, args: list[str], **kwargs) -> None

This module is designed for future refactoring of main.py's inline command handling.
For now, it defines command metadata and handler stubs that match the CLI's /commands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ["Command", "COMMANDS", "find_command"]

from jarvis_cli.client import JarvisClient

# ─── Command definition ───────────────────────────────────────────────────────

CommandHandler = Callable[..., Any]


@dataclass
class Command:
    """A CLI slash command definition."""

    name: str
    help: str
    usage: str = ""
    handler: CommandHandler | None = None
    aliases: list[str] = field(default_factory=list)
    subcommands: list[Command] = field(default_factory=list)

    def full_usage(self) -> str:
        if self.usage:
            return f"/{self.name} {self.usage}"
        return f"/{self.name}"


# ─── Command table ────────────────────────────────────────────────────────────

COMMANDS: list[Command] = [
    Command("help",   "Show this help message"),
    Command("memory", "Access long-term memory",
            usage="search <q> | recent | store <text> | status",
            subcommands=[
                Command("search", "Semantic search in memory", usage="<query>"),
                Command("recent", "Show last 10 memory entries"),
                Command("store",  "Manually store a memory entry", usage="<text>"),
                Command("status", "Show memory system status"),
            ]),
    Command("skills", "Manage learned skills",
            usage="list | new | run <id>",
            subcommands=[
                Command("list", "Show all stored skills"),
                Command("new",  "Create a new skill interactively"),
                Command("run",  "Execute a skill by ID", usage="<skill_id>"),
            ]),
    Command("model",  "View or switch AI model",
            usage="[model_name]",
            aliases=["models"]),
    Command("run",    "Launch an autonomous agent loop for a goal",
            usage="<goal>"),
    Command("tasks",  "List scheduled background tasks"),
    Command("profile","Show your user profile & preferences"),
    Command("clear",  "Clear the terminal screen"),
    Command("quit",   "Exit the CLI",
            aliases=["exit", "q"]),
]


def find_command(name: str) -> Command | None:
    """Look up a command by name or alias (case-insensitive)."""
    name_lower = name.lower()
    for cmd in COMMANDS:
        if cmd.name == name_lower or name_lower in cmd.aliases:
            return cmd
    return None
