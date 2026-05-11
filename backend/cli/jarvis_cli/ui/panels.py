"""Rich UI panels and helper renderers."""
from __future__ import annotations

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def header_banner() -> None:
    banner = Text()
    banner.append("  J.A.R.V.I.S  ", style="bold cyan")
    banner.append("F.R.D.A.Y", style="bold magenta")
    console.print(Panel(banner, border_style="cyan", padding=(0, 4)))


def status_bar(server_url: str, model: str, session_id: str) -> None:
    cols = [
        Text(f"● {server_url}", style="green"),
        Text(f"model: {model or 'auto'}", style="yellow"),
        Text(f"session: {session_id[:12]}", style="dim"),
    ]
    console.print(Columns(cols, equal=False, expand=False), style="dim")


def help_panel() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    commands = [
        ("/memory search <q>", "Semantic search in long-term memory"),
        ("/memory recent",     "Show last 10 conversation turns"),
        ("/memory store <text>","Manually save a memory entry"),
        ("/skills",            "List all stored skills"),
        ("/skills new",        "Create a new skill interactively"),
        ("/skills run <id>",   "Execute a skill by ID"),
        ("/model",             "Show current model + all available"),
        ("/model <name>",      "Switch active model"),
        ("/run <goal>",        "Launch agent loop for a complex goal"),
        ("/tasks",             "List scheduled background tasks"),
        ("/profile",           "Show your user profile"),
        ("/clear",             "Clear the screen"),
        ("/quit  or  /exit",   "Exit the CLI"),
    ]
    for cmd, desc in commands:
        table.add_row(f"[bold cyan]{cmd}[/]", f"[dim]{desc}[/]")
    console.print(Panel(table, title="[bold]Commands[/]", border_style="dim"))


def memory_table(entries: list[dict]) -> None:
    if not entries:
        console.print("[dim]No memory entries found.[/]")
        return
    table = Table(title="Memory", show_lines=True)
    table.add_column("ID", style="dim", width=6)
    table.add_column("Type", width=10)
    table.add_column("Content", overflow="fold")
    table.add_column("Score", width=6)
    for e in entries:
        table.add_row(
            str(e.get("id", "?")),
            e.get("type", "?"),
            e.get("content", "")[:120],
            str(e.get("score", "")),
        )
    console.print(table)


def skills_table(skills: list[dict]) -> None:
    if not skills:
        console.print("[dim]No skills stored yet.[/]")
        return
    table = Table(title="Skills", show_lines=False)
    table.add_column("ID", style="cyan", overflow="fold", max_width=18)
    table.add_column("Name", max_width=30)
    table.add_column("Category", width=12)
    table.add_column("Quality", width=8)
    table.add_column("Runs", width=6)
    table.add_column("Enabled", width=8)
    for s in skills:
        table.add_row(
            s.get("skillId", "?"),
            s.get("name", "?"),
            s.get("category", "?"),
            f"{s.get('qualityScore', 0):.2f}",
            str(s.get("executionCount", 0)),
            "✓" if s.get("enabled") else "✗",
        )
    console.print(table)


def models_table(models: list[dict]) -> None:
    if not models:
        console.print("[dim]No models available.[/]")
        return
    table = Table(title="Available Models", show_lines=False)
    table.add_column("ID", overflow="fold")
    table.add_column("Provider", width=14)
    table.add_column("Context", width=10)
    for m in models:
        table.add_row(
            m.get("id", m.get("name", "?")),
            m.get("providerId", m.get("provider", "?")),
            str(m.get("contextLength", m.get("context_length", "?"))),
        )
    console.print(table)
