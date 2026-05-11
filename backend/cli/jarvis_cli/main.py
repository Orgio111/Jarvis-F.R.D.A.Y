"""
JARVIS CLI — interactive terminal interface
────────────────────────────────────────────
Usage:
  jarvis                     # start interactive chat (auto-connects to localhost:8000)
  jarvis --url http://…      # custom server URL
  jarvis --model gpt-4o      # set preferred model
  jarvis /run "find me…"     # one-shot agentic task, then exit

Inside the REPL, type /help to see all commands.
"""
from __future__ import annotations

import asyncio
import os
import sys
from uuid import uuid4

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text

from jarvis_cli.client import JarvisClient
from jarvis_cli.ui.panels import (
    console, header_banner, help_panel, memory_table,
    models_table, skills_table, status_bar,
)

_HISTORY_FILE = os.path.expanduser("~/.jarvis_cli_history")

_PROMPT_STYLE = Style.from_dict({
    "prompt": "bold cyan",
})


# ─── Main CLI entrypoint ──────────────────────────────────────────────────────

@click.command()
@click.option("--url",     default="http://localhost:8000", envvar="JARVIS_URL",  show_default=True, help="Gateway URL")
@click.option("--model",   default="",                      envvar="JARVIS_MODEL", help="Preferred model ID")
@click.option("--user-id", default="default",               envvar="JARVIS_USER",  help="User ID for profile/memory")
@click.option("--api-key", default="",                      envvar="JARVIS_API_KEY", help="API key")
@click.argument("oneshot", nargs=-1, required=False)
def main(url: str, model: str, user_id: str, api_key: str, oneshot: tuple[str, ...]) -> None:
    """JARVIS — Personal AI Assistant CLI."""
    asyncio.run(_run(url, model, user_id, api_key, " ".join(oneshot)))


async def _run(url: str, model: str, user_id: str, api_key: str, oneshot: str) -> None:
    client = JarvisClient(base_url=url, api_key=api_key)
    session_id = str(uuid4())
    conversation: list[dict] = []

    # Health-check
    try:
        await client.health()
    except Exception:
        console.print(f"[red]✗ Cannot reach JARVIS at {url}[/]")
        console.print("[dim]  Start the backend:  make dev[/]")
        sys.exit(1)

    if oneshot:
        # One-shot agentic run
        await _cmd_run(client, oneshot)
        return

    header_banner()
    status_bar(url, model, session_id)
    console.print("[dim]Type /help for commands, or just chat.[/]\n")

    session = PromptSession(
        history=FileHistory(_HISTORY_FILE),
        auto_suggest=AutoSuggestFromHistory(),
        style=_PROMPT_STYLE,
    )

    while True:
        try:
            user_input: str = await session.prompt_async("you › ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # ── Slash commands ────────────────────────────────────────────────────
        if user_input.startswith("/"):
            parts = user_input[1:].split(maxsplit=2)
            cmd = parts[0].lower() if parts else ""
            args = parts[1:] if len(parts) > 1 else []
            rest = " ".join(args)

            if cmd in ("quit", "exit", "q"):
                console.print("[dim]Goodbye.[/]")
                break

            elif cmd == "help":
                help_panel()

            elif cmd == "clear":
                console.clear()
                header_banner()

            elif cmd == "memory":
                await _handle_memory(client, args)

            elif cmd == "skills":
                await _handle_skills(client, args)

            elif cmd == "model":
                if rest:
                    model = rest
                    console.print(f"[green]Model switched to:[/] {model}")
                    status_bar(url, model, session_id)
                else:
                    models = await client.models_list()
                    models_table(models)

            elif cmd == "run":
                goal = rest or click.prompt("Goal")
                await _cmd_run(client, goal)

            elif cmd == "tasks":
                tasks = await client.scheduler_tasks()
                if not tasks:
                    console.print("[dim]No scheduled tasks.[/]")
                else:
                    for t in tasks:
                        console.print(
                            f"  [cyan]{t['taskId']}[/]  {t['name']}  "
                            f"[dim]({t['triggerType']}, runs: {t['runCount']})[/]"
                        )

            elif cmd == "profile":
                async with __import__("httpx").AsyncClient(timeout=10) as hc:
                    r = await hc.get(f"{client.base_url}/profile", headers=client._headers)
                    data = r.json().get("data", {})
                prefs = data.get("preferences", {})
                goals = data.get("goals", {})
                console.print(f"[bold]Preferences:[/] {prefs}")
                console.print(f"[bold]Goals:[/] {goals}")

            else:
                console.print(f"[yellow]Unknown command:[/] /{cmd}  (type /help)")

            continue

        # ── Normal chat message ────────────────────────────────────────────────
        conversation.append({"role": "user", "content": user_input})

        full_response = await _stream_chat(
            client, conversation, model, session_id, user_id
        )

        if full_response:
            conversation.append({"role": "assistant", "content": full_response})
        # Keep context window manageable (last 30 turns)
        if len(conversation) > 60:
            conversation = conversation[-60:]


# ─── Chat streaming ───────────────────────────────────────────────────────────

async def _stream_chat(
    client: JarvisClient,
    messages: list[dict],
    model: str,
    session_id: str,
    user_id: str,
) -> str:
    console.print()
    collected: list[str] = []

    try:
        with Live(console=console, refresh_per_second=20) as live:
            live.update(Text("▌", style="cyan blink"))
            async for event in client.chat_stream(messages, model, session_id, user_id):
                etype = event.get("event", "")
                if etype == "CHAT_STREAM_TOKEN":
                    collected.append(event.get("data", {}).get("token", ""))
                    live.update(Markdown("".join(collected)))
                elif etype == "CHAT_STREAM_END":
                    full = event.get("data", {}).get("content", "".join(collected))
                    live.update(Markdown(full))
                    console.print()
                    return full
                elif etype == "CHAT_STREAM_ERROR":
                    live.update(Text(f"Error: {event.get('data', {}).get('error', 'unknown')}", style="red"))
                    console.print()
                    return ""
    except Exception as exc:
        console.print(f"\n[red]Stream error:[/] {exc}")
        return ""

    result = "".join(collected)
    if result:
        console.print(Markdown(result))
    console.print()
    return result


# ─── /memory sub-commands ─────────────────────────────────────────────────────

async def _handle_memory(client: JarvisClient, args: list[str]) -> None:
    sub = args[0].lower() if args else "status"
    rest = " ".join(args[1:])

    if sub == "status":
        st = await client.memory_status()
        console.print(
            f"  Total entries: [cyan]{st.get('totalEntries', '?')}[/]  "
            f"FAISS vectors: [cyan]{st.get('faissVectors', '?')}[/]  "
            f"Embeddings: {'✓' if st.get('embeddingsAvailable') else '✗'}"
        )

    elif sub == "search":
        query = rest or click.prompt("Search query")
        with console.status("Searching memory…"):
            results = await client.memory_search(query, top_k=8)
        memory_table(results)

    elif sub == "recent":
        with console.status("Loading recent memory…"):
            entries = await client.memory_recent(limit=10)
        memory_table(entries)

    elif sub == "store":
        content = rest or click.prompt("Content to store")
        r = await client.memory_store(content)
        console.print(f"[green]Stored[/] memory id={r.get('id')}")

    else:
        console.print("[dim]/memory status | search <q> | recent | store <text>[/]")


# ─── /skills sub-commands ────────────────────────────────────────────────────

async def _handle_skills(client: JarvisClient, args: list[str]) -> None:
    sub = args[0].lower() if args else "list"
    rest = " ".join(args[1:])

    if sub == "list" or sub == "":
        with console.status("Loading skills…"):
            skills = await client.skills_list()
        skills_table(skills)

    elif sub == "new":
        name = rest or click.prompt("Skill name")
        description = click.prompt("Description")
        category = click.prompt("Category", default="general")
        with console.status(f"Generating skill '{name}'…"):
            skill = await client.skill_create(name, description, category)
        console.print(f"[green]Created skill[/] {skill.get('skillId')} — v{skill.get('version')}")

    elif sub == "run":
        skill_id = rest or click.prompt("Skill ID")
        with console.status(f"Running skill {skill_id}…"):
            result = await client.skill_run(skill_id)
        console.print(result)

    else:
        console.print("[dim]/skills list | new | run <id>[/]")


# ─── /run agent loop ──────────────────────────────────────────────────────────

async def _cmd_run(client: JarvisClient, goal: str) -> None:
    console.print(f"\n[bold cyan]Agent:[/] {goal}\n")

    async for event in client.agent_run_stream(goal, max_iterations=3):
        etype = event.get("event", "")

        if etype == "AGENT_START":
            console.print(f"[dim]Run ID: {event.get('runId')}[/]")

        elif etype == "AGENT_PLANNING":
            console.print(f"[yellow]● Planning (iteration {event.get('iteration')})…[/]")

        elif etype == "AGENT_PLAN_READY":
            steps = event.get("steps", [])
            for i, s in enumerate(steps, 1):
                console.print(f"  [dim]{i}.[/] {s.get('instruction', s)[:100]}")

        elif etype == "AGENT_STEP_START":
            console.print(f"  [cyan]→[/] Step {event.get('stepIndex', 0) + 1}: {str(event.get('step', ''))[:80]}")

        elif etype == "AGENT_STEP_DONE":
            result = event.get("result", {})
            if result.get("success") is False:
                console.print(f"    [red]✗[/] {result.get('error', 'failed')[:100]}")
            else:
                out = str(result.get("output", ""))[:120]
                if out:
                    console.print(f"    [green]✓[/] {out}")

        elif etype == "AGENT_REFLECTING":
            console.print(f"[yellow]● Evaluating…[/]")

        elif etype == "AGENT_REFLECTION":
            satisfied = event.get("satisfied", False)
            icon = "[green]✓[/]" if satisfied else "[yellow]↺[/]"
            console.print(f"{icon} {event.get('feedback', '')[:120]}")

        elif etype == "AGENT_DONE":
            answer = event.get("finalAnswer", "")
            if answer:
                console.print(f"\n[bold]Answer:[/]")
                console.print(Markdown(answer))
            console.print(
                f"\n[dim]Done in {event.get('elapsedMs', '?')} ms, "
                f"{event.get('totalActions', 0)} actions, "
                f"{event.get('iterations', 0)} iterations.[/]\n"
            )


if __name__ == "__main__":
    main()
