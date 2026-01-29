"""CLI entry point and UI for Planning Agent."""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from artifacts import compute_diff, display_artifacts, save_plan_artifact
from config import CONFIG_DIR, interactive_setup, is_configured, load_config
from gantt_chart import export_gantt_chart
from graph import app, context_management_node
from import_export import export_plan_to_file, import_plan_from_file
from llm_providers import get_current_provider_info, switch_provider
from sessions import SessionManager, SessionOperations
from templates import TemplateApplicator, TemplateRegistry
from tools import UndoRedoManager, get_plan_statistics

load_dotenv()

logging.basicConfig(
    filename=CONFIG_DIR / "agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

config = load_config()
if config.get("provider") == "bedrock":
    os.environ["LLM_PROVIDER"] = "bedrock"
    os.environ["BEDROCK_MODEL"] = config.get(
        "bedrock_model", "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    if config.get("aws_region"):
        os.environ["AWS_REGION"] = config["aws_region"]
    if config.get("bedrock_api_key"):
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = config["bedrock_api_key"]
    if config.get("aws_access_key_id"):
        os.environ["AWS_ACCESS_KEY_ID"] = config["aws_access_key_id"]
    if config.get("aws_secret_access_key"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = config["aws_secret_access_key"]
elif config.get("provider") == "anthropic":
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["ANTHROPIC_MODEL"] = config.get("anthropic_model", "claude-sonnet-4-5-20250929")
    if config.get("anthropic_api_key"):
        os.environ["ANTHROPIC_API_KEY"] = config["anthropic_api_key"]

console = Console()
USER_COLOR = "bright_cyan"
AGENT_COLOR = "bright_magenta"

TOOL_INFO = {
    "create_plan": ("Creating your plan...", "green"),
    "update_plan": ("Proposing changes...", "blue"),
    "detect_ambiguity": ("Understanding your request...", "yellow"),
    "ask_clarifying_question": ("Thinking about what to ask...", "yellow"),
    "generate_plan_summary": ("Preparing summary...", "cyan"),
    "generate_plan_diff": ("Checking changes...", "cyan"),
    "generate_executive_summary": ("Summarizing conversation...", "cyan"),
    "appknox_security_audit": ("Analyzing security...", "red"),
    "export_plan": ("Exporting...", "magenta"),
    "get_plan_statistics": ("Calculating...", "dim"),
    "validate_plan": ("Validating plan...", "yellow"),
    "assess_plan_risks": ("Assessing risks...", "orange3"),
    "estimate_plan_duration": ("Estimating duration...", "cyan"),
    "suggest_plan_improvements": ("Analyzing improvements...", "green"),
    "fork_plan": ("Forking plan...", "blue"),
    "mark_milestone": ("Marking milestone...", "gold1"),
}

session_manager = SessionManager()
session_ops = SessionOperations(session_manager)
undo_redo_manager = UndoRedoManager()
template_applicator = TemplateApplicator()
template_registry = TemplateRegistry()


def normalize_content(content):
    """Normalize message content to string."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        result = []
        for item in content:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    result.append(item["text"])
                elif "content" in item:
                    result.append(item["content"])
        return "\n".join(result)
    else:
        return str(content)


def print_welcome():
    """Print welcome message with provider info."""
    info = get_current_provider_info()
    status = "●" if info["available"] else "○"
    console.print(f"[dim]Planning Agent | {info['provider']}:{info['model']} {status}[/dim]")


def print_help():
    """Print help text for CLI commands."""
    help_text = """Commands:
  /config        Configure LLM provider
  /provider      Switch provider (bedrock/anthropic)
  /update        Update plan-agent to latest version

  Session Commands:
  /save          Save current session
  /sessions      List saved sessions
  /resume <id>   Resume a saved session
  /fork          Fork current session
  /search <q>    Search sessions
  /tag <tags>    Tag current session

  Template Commands:
  /templates     List available templates
  /use <id>      Create plan from template

  Plan Commands:
  /plan          Show current plan
  /stats         Show plan statistics
  /gantt         Export Gantt chart (html/svg)
  /export <fmt>  Export plan (md/json/html/csv)
  /import <file> Import plan from file

  Edit Commands:
  /undo          Undo last change
  /redo          Redo last undone change
  /diff          Show changes from last edit
  /compact [id]  Compact current session or saved session

  Utility Commands:
  /artifacts     List saved plan files
  /multi         Multiline input
  /clear         Clear screen
  /reset         New session
  /exit or exit  Quit
  Ctrl+C         Also quits

Tip: Type / and press ENTER for interactive menu with arrow keys"""
    console.print(f"[dim]{help_text}[/dim]")


def display_user_message(text):
    """Display user message."""
    console.print(f"[{USER_COLOR}]{text}[/{USER_COLOR}]")


def display_agent_message(content):
    """Display agent message with markdown formatting."""
    console.print(Markdown(content))


def display_plan(plan):
    """Display current plan in formatted table."""
    if not plan:
        console.print("[dim]No plan created yet.[/dim]")
        return

    title = plan.get("title", "Untitled")
    version = plan.get("version", 1)
    steps = plan.get("steps", [])
    completed = sum(1 for s in steps if s.get("status") == "completed")
    metadata = plan.get("metadata", {})
    milestones = set(metadata.get("milestones", []))

    console.print(f"[bold]{title}[/bold] (v{version}) - {completed}/{len(steps)} done")

    if metadata.get("estimated_duration"):
        console.print(f"[dim]Estimated: {metadata['estimated_duration']}[/dim]")

    console.print()

    for step in steps:
        status = "✓" if step.get("status") == "completed" else "○"
        milestone = " 🏁" if step["id"] in milestones else ""
        due = ""
        if "due_date" in step:
            due_date = (
                step["due_date"][:10]
                if isinstance(step["due_date"], str)
                else str(step["due_date"])[:10]
            )
            due = f" [dim](due {due_date})[/dim]"

        console.print(f"  {status} {step['id']}.{milestone} {step.get('description', '')}{due}")

        if "sub_steps" in step:
            for sub in step["sub_steps"]:
                sub_status = "✓" if sub.get("status") == "completed" else "○"
                console.print(f"      {sub_status} {sub['description']}")


def display_stats(plan):
    """Display plan statistics."""
    if not plan:
        console.print("[dim]No plan to analyze.[/dim]")
        return

    stats = get_plan_statistics.invoke({"plan": plan})
    metadata = plan.get("metadata", {})

    console.print(f"[bold]{stats['title']}[/bold]")
    console.print(f"  Steps: {stats['total_steps']} total")
    console.print(f"  ✓ {stats['completed_steps']} completed")
    console.print(f"  ○ {stats['pending_steps']} pending")
    console.print(f"  Completion: {stats['completion_percentage']}%")

    if metadata.get("estimated_duration"):
        console.print(f"  Estimated Duration: {metadata['estimated_duration']}")

    deps = metadata.get("dependencies", {})
    if deps:
        console.print(f"  Dependencies: {len(deps)} step relationships")

    milestones = metadata.get("milestones", [])
    if milestones:
        console.print(f"  Milestones: {len(milestones)} marked")


def display_sessions(sessions: list[dict[str, Any]]):
    """Display saved sessions in a table."""
    if not sessions:
        console.print("[dim]No saved sessions found.[/dim]")
        return

    table = Table(title="Saved Sessions")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="green")
    table.add_column("Size", justify="right", style="dim")
    table.add_column("Updated", style="dim")
    table.add_column("Msgs", justify="right")
    table.add_column("Tags", style="yellow")

    for session in sessions[:20]:
        tags = ", ".join(session.get("tags", [])) or "-"
        size = session.get("size_kb", 0)
        size_str = f"{size:.1f} KB" if size < 1024 else f"{size / 1024:.1f} MB"

        table.add_row(
            session["session_id"][:12],
            session["title"][:35],
            size_str,
            session["updated_at"][:16].replace("T", " ")
            if "T" in session["updated_at"]
            else session["updated_at"][:16],
            str(session.get("message_count", 0)),
            tags[:25],
        )

    console.print(table)


def display_templates():
    """Display available plan templates."""
    templates = template_registry.list_templates()
    categories = template_registry.get_categories()

    console.print("[bold]Available Templates[/bold]\n")

    for category in categories:
        console.print(f"[cyan]{category.title()}[/cyan]")
        category_templates = [t for t in templates if t.category == category]
        for template in category_templates:
            console.print(f"  [green]{template.id}[/green] - {template.name}")
            console.print(f"    [dim]{template.description}[/dim]")
            if template.estimated_duration:
                console.print(f"    [dim]~{template.estimated_duration}[/dim]")
        console.print()


def get_input():
    """Get single line input from user with interactive menu."""
    from completer import get_input_with_menu

    return get_input_with_menu()


def get_multiline_input():
    """Get multiline input from user."""
    lines = []
    console.print("[dim]Enter text (empty line to finish):[/dim]")
    while True:
        line = console.input("  ")
        if line.strip() == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines)


def update_plan_agent():
    """Update plan-agent to latest version."""
    install_path = os.path.expanduser("~/.local/share/plan-agent")

    if not os.path.isdir(install_path):
        console.print("[red]Error: plan-agent not found at ~/.local/share/plan-agent[/red]")
        console.print("[dim]You may need to reinstall from GitHub.[/dim]")
        return False

    console.print("[dim]Checking for updates...[/dim]")

    try:
        import tarfile
        import tempfile
        import urllib.request

        repo_url = "https://github.com/Sarvesh-GanesanW/PlannerAgent"
        tmp_dir = tempfile.mkdtemp()
        tar_path = os.path.join(tmp_dir, "plan-agent.tar.gz")

        console.print("[dim]Downloading latest version...[/dim]")
        urllib.request.urlretrieve(f"{repo_url}/archive/refs/heads/main.tar.gz", tar_path)

        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(tmp_dir)

        extracted_path = os.path.join(tmp_dir, "PlannerAgent-main")

        uv_path = os.path.expanduser("~/.cargo/bin/uv")
        if not os.path.exists(uv_path):
            uv_path = os.path.expanduser("~/.local/bin/uv")

        console.print("[dim]Updating files...[/dim]")
        import shutil

        for item in os.listdir(extracted_path):
            src = os.path.join(extracted_path, item)
            dst = os.path.join(install_path, item)

            if item == ".venv":
                continue

            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        console.print("[dim]Updating dependencies...[/dim]")
        venv_python = os.path.join(install_path, ".venv", "bin", "python")

        if os.path.exists(uv_path):
            subprocess.run(
                [
                    uv_path,
                    "pip",
                    "install",
                    "-q",
                    "--python",
                    venv_python,
                    "-r",
                    os.path.join(install_path, "requirements.txt"),
                ],
                check=True,
                capture_output=True,
            )
        else:
            subprocess.run(
                [
                    venv_python,
                    "-m",
                    "pip",
                    "install",
                    "-q",
                    "-r",
                    os.path.join(install_path, "requirements.txt"),
                ],
                check=True,
                capture_output=True,
            )

        shutil.rmtree(tmp_dir)

        console.print("[green]✓ plan-agent updated successfully![/green]")
        console.print("[dim]Restart plan-agent to use the new version.[/dim]")
        return True

    except Exception as e:
        console.print(f"[red]Error updating: {e}[/red]")
        return False


async def get_response(state):
    """Get response from agent and handle streaming with interrupt support."""
    current_plan = None
    new_summary = None
    new_messages = []
    final_content = None
    interrupted = False

    shared_state = {
        "current_tool": None,
        "tool_start_time": None,
        "done": False,
        "final_content": None,
        "last_diff": None,
        "interrupted": False,
    }

    async def stream_response():
        nonlocal current_plan, new_summary, new_messages, final_content

        try:
            async for event in app.astream(state):
                if shared_state["interrupted"]:
                    break

                for key, value in event.items():
                    if "messages" in value:
                        for msg in value["messages"]:
                            new_messages.append(msg)

                            if isinstance(msg, AIMessage):
                                content_str = normalize_content(msg.content)
                                if content_str.strip():
                                    shared_state["final_content"] = content_str
                                    logging.info(f"LLM Response: {content_str}")

                                if hasattr(msg, "tool_calls") and msg.tool_calls:
                                    for tc in msg.tool_calls:
                                        tool_name = tc.get("name")
                                        if tool_name:
                                            shared_state["current_tool"] = tool_name
                                            shared_state["tool_start_time"] = time.time()
                                            logging.info(f"Tool Call: {tool_name}")

                    if "current_plan" in value:
                        current_plan = value["current_plan"]
                        if current_plan:
                            filepath, diff = save_plan_artifact(current_plan)
                            shared_state["last_diff"] = diff
                            console.print(f"[dim]💾 Plan saved to: {filepath}[/dim]")
                            logging.info(f"Plan saved to {filepath}")

                    if "summary" in value:
                        new_summary = value["summary"]
        except asyncio.CancelledError:
            shared_state["interrupted"] = True
            raise

        shared_state["done"] = True
        final_content = shared_state["final_content"]

    stream_task = asyncio.create_task(stream_response())

    # Keyboard interrupt handling
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    breathe_dots = ["○", "◒", "◐", "◕", "●", "◕", "◐", "◒"]
    idx = 0
    active_tool = None

    try:
        tty.setcbreak(fd)  # Enable non-blocking character input

        with Live(
            Text("○ Thinking... (ESC to stop)", style="dim"),
            refresh_per_second=10,
            transient=True,
            console=console,
        ) as live:
            while not stream_task.done():
                # Check for Escape key
                if select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1)
                    if ch == "\x1b":  # Escape key
                        shared_state["interrupted"] = True
                        interrupted = True
                        stream_task.cancel()
                        live.update(Text("⚠ Stopping...", style="yellow"))
                        break
                    elif ch == "\x03":  # Ctrl+C
                        raise KeyboardInterrupt

                current_tool = shared_state.get("current_tool")

                if current_tool:
                    active_tool = current_tool

                if active_tool and active_tool in TOOL_INFO:
                    display_text, base_color = TOOL_INFO[active_tool]
                elif active_tool:
                    display_text = f"Using {active_tool}..."
                    base_color = "bright_magenta"
                else:
                    display_text = "Thinking... (ESC to stop)"
                    base_color = "bright_magenta"

                dot = breathe_dots[idx % len(breathe_dots)]

                pulse_phase = idx % 6
                if pulse_phase < 2:
                    color = f"bold {base_color}"
                elif pulse_phase < 4:
                    color = base_color
                else:
                    color = f"dim {base_color}"

                live.update(Text(f"{dot} {display_text}", style=color))
                idx += 1
                await asyncio.sleep(0.1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    try:
        await stream_task
    except asyncio.CancelledError:
        interrupted = True
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.error(f"Error in stream_task: {e}")

    if interrupted:
        console.print("[yellow]⚠ Generation stopped by user[/yellow]")
        logging.info("Generation interrupted by user")
    elif final_content:
        display_agent_message(final_content)
        console.print()

    diff = shared_state.get("last_diff")
    if diff:
        has_changes = any(action != "same" for action, _, _ in diff)
        if has_changes:
            console.print("[dim]Changes saved:[/dim]")
            for action, old, new in diff[:10]:
                if action == "add":
                    console.print(f"  [green]+ {new[:60]}[/green]")
                elif action == "remove":
                    console.print(f"  [red]- {old[:60]}[/red]")
                elif action == "modify":
                    console.print(f"  [red]- {old[:50]}[/red]")
                    console.print(f"  [green]+ {new[:50]}[/green]")
            console.print()

    return current_plan, new_summary, new_messages


def handle_command(cmd: str, arg: str, state: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Handle CLI commands. Returns (should_continue, new_state)."""

    if cmd == "/exit":
        console.print("[dim]Goodbye! 👋 Happy planning![/dim]")
        return False, state

    elif cmd == "/help":
        print_help()
        return True, state

    elif cmd == "/config":
        interactive_setup()
        print_welcome()
        return True, state

    elif cmd == "/provider":
        if not arg:
            info = get_current_provider_info()
            console.print(f"[dim]Current: {info['provider']}[/dim]")
            return True, state

        parts = arg.split()
        if switch_provider(parts[0], parts[1] if len(parts) > 1 else None):
            console.print(f"[green]Switched to {parts[0]}[/green]")
        else:
            console.print("[red]Failed. Check API key.[/red]")
        return True, state

    elif cmd == "/update":
        update_plan_agent()
        return True, state

    elif cmd == "/clear":
        console.clear()
        print_welcome()
        return True, state

    elif cmd == "/reset":
        return True, create_fresh_state()

    elif cmd == "/plan":
        display_plan(state.get("current_plan"))
        return True, state

    elif cmd == "/stats":
        display_stats(state.get("current_plan"))
        return True, state

    elif cmd == "/gantt":
        plan = state.get("current_plan")
        if not plan:
            console.print("[red]No plan to chart.[/red]")
            return True, state

        format = arg.strip() if arg else "html"
        if format not in ["html", "svg"]:
            console.print("[red]Usage: /gantt [html|svg][/red]")
            return True, state

        try:
            content = export_gantt_chart(plan, format)

            # Save to artifacts
            from artifacts import sanitize_filename

            base_name = sanitize_filename(plan.get("title", "plan"))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base_name}_gantt_{timestamp}.{format}"
            filepath = Path("artifacts") / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)

            console.print(f"[green]✓ Gantt chart exported: {filepath}[/green]")

            # Try to open in browser if html
            if format == "html":
                import webbrowser

                try:
                    webbrowser.open(f"file://{filepath.absolute()}")
                    console.print("[dim]Opening in browser...[/dim]")
                except Exception:
                    pass
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        return True, state

    elif cmd == "/":
        display_artifacts()
        return True, state

    elif cmd == "/compact":
        if arg:
            # Compact a saved session
            success = session_manager.compact_session(arg.strip())
            if success:
                new_size = session_manager.get_session_size(arg.strip())
                console.print(f"[green]✓ Session compacted: {arg[:12]}[/green]")
                console.print(f"[dim]New size: {new_size / 1024:.1f} KB[/dim]")
            else:
                console.print(f"[red]Session not found: {arg}[/red]")
        else:
            # Compact current context
            console.print("[dim]Compacting context...[/dim]")
            result = context_management_node(state)
            if result.get("summary"):
                state["summary"] = result["summary"]
            if result.get("messages"):
                state["messages"] = result["messages"]
            console.print("[green]✓ Context compacted.[/green]")
        return True, state

    elif cmd == "/save":
        session_id = session_manager.auto_save(state)
        console.print(f"[green]✓ Session saved: {session_id[:12]}[/green]")
        return True, state

    elif cmd == "/sessions":
        sessions = session_manager.list_sessions()
        display_sessions(sessions)
        return True, state

    elif cmd == "/resume":
        if not arg:
            console.print("[red]Usage: /resume <session_id>[/red]")
            sessions = session_manager.list_sessions()[:5]
            if sessions:
                console.print("[dim]Recent sessions:[/dim]")
                for s in sessions:
                    console.print(f"  [cyan]{s['session_id'][:12]}[/cyan] - {s['title']}")
            return True, state

        loaded_state = session_manager.load(arg.strip())
        if loaded_state:
            console.print(
                f"[green]✓ Resumed session: {loaded_state.get('title', arg[:12])}[/green]"
            )
            display_plan(loaded_state.get("current_plan"))
            return True, loaded_state
        else:
            console.print(f"[red]Session not found: {arg}[/red]")
            return True, state

    elif cmd == "/fork":
        current_session = state.get("session_id")
        if not current_session:
            console.print("[red]No current session to fork. Use /save first.[/red]")
            return True, state

        new_title = arg if arg else f"{state.get('title', 'Session')} (Copy)"
        new_id = session_manager.fork(current_session, new_title)
        if new_id:
            console.print(f"[green]✓ Forked to new session: {new_id[:12]}[/green]")
        return True, state

    elif cmd == "/search":
        if not arg:
            console.print("[red]Usage: /search <query>[/red]")
            return True, state

        results = session_manager.search(arg)
        if results:
            console.print(f"[green]Found {len(results)} matching sessions:[/green]")
            display_sessions(results)
        else:
            console.print("[dim]No matching sessions found.[/dim]")
        return True, state

    elif cmd == "/tag":
        if not arg:
            console.print("[red]Usage: /tag <tag1,tag2,...>[/red]")
            return True, state

        tags = [t.strip() for t in arg.split(",")]
        current_tags = set(state.get("tags", []))
        current_tags.update(tags)
        state["tags"] = list(current_tags)

        if state.get("session_id"):
            session_manager.save(state["session_id"], state, tags=list(current_tags))

        console.print(f"[green]✓ Tags added: {', '.join(tags)}[/green]")
        return True, state

    elif cmd == "/undo":
        previous_plan, new_state = undo_redo_manager.undo(state)
        if previous_plan is not None:
            state["current_plan"] = previous_plan
            state["undo_stack"] = new_state["undo_stack"]
            state["redo_stack"] = new_state["redo_stack"]
            console.print("[green]✓ Undone[/green]")
            display_plan(previous_plan)
        else:
            console.print("[dim]Nothing to undo[/dim]")
        return True, state

    elif cmd == "/redo":
        next_plan, new_state = undo_redo_manager.redo(state)
        if next_plan is not None:
            state["current_plan"] = next_plan
            state["undo_stack"] = new_state["undo_stack"]
            state["redo_stack"] = new_state["redo_stack"]
            console.print("[green]✓ Redone[/green]")
            display_plan(next_plan)
        else:
            console.print("[dim]Nothing to redo[/dim]")
        return True, state

    elif cmd == "/diff":
        """Show diff between plans. Usage: /diff [file1] [file2]"""
        from artifacts import diff_artifacts, ARTIFACTS_DIR
        
        args = arg.strip().split() if arg else []
        
        if len(args) == 0:
            # Show diff from last change
            diff = shared_state.get("last_diff") if 'shared_state' in globals() else None
            if not diff:
                # Try to compute diff from undo stack
                undo_stack = state.get("undo_stack", [])
                current_plan = state.get("current_plan")
                if undo_stack and current_plan:
                    diff = compute_diff(undo_stack[-1], current_plan)
                elif current_plan:
                    console.print("[dim]No previous version to compare. This is a new plan.[/dim]")
                    return True, state
                else:
                    console.print("[red]No plan to diff.[/red]")
                    return True, state
        elif len(args) == 1:
            # Compare with previous version of this file
            diff = diff_artifacts(args[0])
            if diff is None:
                console.print(f"[red]Could not find artifact or previous version: {args[0]}[/red]")
                console.print(f"[dim]Artifacts are stored in: {ARTIFACTS_DIR}[/dim]")
                return True, state
        elif len(args) >= 2:
            # Compare two specific files
            diff = diff_artifacts(args[0], args[1])
            if diff is None:
                console.print(f"[red]Could not find one or both artifacts.[/red]")
                console.print(f"[dim]Artifacts are stored in: {ARTIFACTS_DIR}[/dim]")
                return True, state
        
        has_changes = any(action != "same" for action, _, _ in diff)
        if not has_changes:
            console.print("[dim]No changes between versions.[/dim]")
            return True, state
        
        console.print("\n[bold]Changes:[/bold]")
        console.print("─" * 50)
        for action, old, new in diff:
            if action == "title":
                console.print(f"[yellow]Title:[/yellow] [dim]{old}[/dim] → {new}")
            elif action == "add":
                console.print(f"  [green]+ {new[:70]}[/green]")
            elif action == "remove":
                console.print(f"  [red]- {old[:70]}[/red]")
            elif action == "modify":
                console.print(f"  [red]- {old[:70]}[/red]")
                console.print(f"  [green]+ {new[:70]}[/green]")
        console.print("─" * 50 + "\n")
        return True, state

    elif cmd == "/templates":
        display_templates()
        return True, state

    elif cmd == "/use":
        if not arg:
            console.print("[red]Usage: /use <template_id>[/red]")
            console.print("[dim]Use /templates to see available templates[/dim]")
            return True, state

        template_id = arg.strip()
        preview = template_applicator.get_template_preview(template_id)

        if preview:
            new_plan = template_applicator.apply_template(template_id)
            state["current_plan"] = new_plan
            console.print(f"[green]✓ Created plan from template: {preview['name']}[/green]")
            display_plan(new_plan)

            state = undo_redo_manager.push_state(state, new_plan)
        else:
            console.print(f"[red]Template not found: {template_id}[/red]")
        return True, state

    elif cmd == "/export":
        plan = state.get("current_plan")
        if not plan:
            console.print("[red]No plan to export.[/red]")
            return True, state

        format = arg.strip() if arg else "markdown"
        try:
            filepath = export_plan_to_file(plan, format)
            console.print(f"[green]✓ Exported to: {filepath}[/green]")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
        return True, state

    elif cmd == "/import":
        if not arg:
            console.print("[red]Usage: /import <filepath>[/red]")
            return True, state

        imported = import_plan_from_file(arg.strip())
        if imported:
            state["current_plan"] = imported
            console.print(f"[green]✓ Imported plan: {imported['title']}[/green]")
            display_plan(imported)
        else:
            console.print(f"[red]Failed to import from: {arg}[/red]")
        return True, state

    elif cmd == "/multi":
        return "multi", state

    elif cmd == "/":
        from completer import CommandCompleter

        console.print("[bold]Available commands:[/bold]")
        for cmd in CommandCompleter.COMMANDS:
            console.print(f"  [cyan]{cmd}[/cyan]")
        return True, state

    else:
        console.print(f"[dim]Unknown command: {cmd}[/dim]")
        return True, state


def create_fresh_state() -> dict[str, Any]:
    """Create a fresh agent state."""
    return {
        "messages": [],
        "summary": "",
        "current_plan": {},
        "conversation_turn": 0,
        "user_preferences": {},
        "last_action": "",
        "session_id": "",
        "undo_stack": [],
        "redo_stack": [],
        "tags": [],
    }


async def run_chat(resume_session_id: str | None = None):
    """Main chat loop."""
    if not is_configured():
        print("No LLM configured. Running setup...\n")
        interactive_setup()

    print_welcome()

    if resume_session_id:
        state = session_manager.load(resume_session_id)
        if state:
            console.print(
                f"[green]✓ Resumed session: {state.get('title', resume_session_id[:12])}[/green]"
            )
            display_plan(state.get("current_plan"))
        else:
            console.print(f"[red]Session not found: {resume_session_id}[/red]")
            state = create_fresh_state()
    else:
        state = create_fresh_state()

    turn_count = state.get("conversation_turn", 0)

    while True:
        try:
            user_text = get_input().strip()

            if not user_text:
                continue

            if user_text.lower() == "exit":
                console.print("[dim]Goodbye! 👋 Happy planning![/dim]")
                break

            if user_text.startswith("/"):
                cmd_parts = user_text.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

                result, state = handle_command(cmd, arg, state)

                if result is False:
                    break
                elif result == "multi":
                    user_text = get_multiline_input()
                    if not user_text.strip():
                        continue
                    message = HumanMessage(content=user_text)
                else:
                    continue
            else:
                message = HumanMessage(content=user_text)

            logging.info(f"User Input: {user_text}")

            current_plan = state.get("current_plan")
            if current_plan:
                state = undo_redo_manager.push_state(state, current_plan)

            turn_count += 1
            state["messages"] = state["messages"] + [message]

            new_plan, new_summary, new_messages = await get_response(state)

            if new_messages:
                state["messages"] = state["messages"] + new_messages
            if new_plan:
                state["current_plan"] = new_plan
            if new_summary:
                state["summary"] = new_summary
            state["conversation_turn"] = turn_count

            if state.get("session_id"):
                session_manager.auto_save(state)

            console.print()
            console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye! 👋 Happy planning![/dim]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logging.error(f"Error in run_chat: {e}")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Planning Agent CLI")
    parser.add_argument("command", nargs="?", help="Command to run (config, artifacts, sessions)")
    parser.add_argument("--resume", "-r", help="Resume a saved session by ID")
    parser.add_argument("--list-sessions", "-l", action="store_true", help="List saved sessions")
    parser.add_argument("--templates", "-t", action="store_true", help="List available templates")

    args = parser.parse_args()

    if args.list_sessions:
        sessions = session_manager.list_sessions()
        display_sessions(sessions)
        return

    if args.templates:
        display_templates()
        return

    if args.command == "config":
        interactive_setup()
    elif args.command == "artifacts":
        display_artifacts()
    elif args.command == "sessions":
        sessions = session_manager.list_sessions()
        display_sessions(sessions)
    else:
        asyncio.run(run_chat(resume_session_id=args.resume))


if __name__ == "__main__":
    main()
