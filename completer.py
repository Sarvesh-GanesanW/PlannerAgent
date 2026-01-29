"""Interactive menu and tab completion for CLI with readline support."""

import readline
import sys
from pathlib import Path


class InteractiveMenu:
    """Interactive menu with arrow key navigation."""

    COMMANDS = [
        ("/config", "Configure LLM provider"),
        ("/provider", "Switch provider (bedrock/anthropic)"),
        ("/update", "Update plan-agent to latest version"),
        ("/save", "Save current session"),
        ("/sessions", "List saved sessions"),
        ("/resume", "Resume a saved session"),
        ("/fork", "Fork current session"),
        ("/search", "Search sessions"),
        ("/tag", "Tag current session"),
        ("/templates", "List available templates"),
        ("/use", "Create plan from template"),
        ("/plan", "Show current plan"),
        ("/stats", "Show plan statistics"),
        ("/gantt", "Export Gantt chart (html/svg)"),
        ("/export", "Export plan (md/json/html/csv)"),
        ("/import", "Import plan from file"),
        ("/undo", "Undo last change"),
        ("/redo", "Redo last undone change"),
        ("/diff", "Show changes from last edit"),
        ("/compact", "Compact current session or saved session"),
        ("/artifacts", "List saved plan files"),
        ("/multi", "Multiline input"),
        ("/clear", "Clear screen"),
        ("/reset", "New session"),
        ("/exit", "Quit"),
        ("/help", "Show help"),
    ]

    def __init__(self):
        self._commands = [cmd for cmd, _ in self.COMMANDS]
        self._descriptions = {cmd: desc for cmd, desc in self.COMMANDS}

    def show_menu(self, filter_text: str = "") -> str | None:
        """Show interactive menu and return selected command."""
        # Filter commands
        if filter_text:
            items = [(cmd, desc) for cmd, desc in self.COMMANDS if cmd.startswith(filter_text)]
        else:
            items = self.COMMANDS[:]

        if not items:
            return None

        if len(items) == 1:
            return items[0][0]

        # Use simple selection menu (more reliable than terminal manipulation)
        return self._select_from_menu(items)

    def _select_from_menu(self, items: list[tuple[str, str]]) -> str | None:
        """Show menu and let user select with simple input."""
        print("\n  Available commands:")
        print("  " + "─" * 50)

        for i, (cmd, desc) in enumerate(items, 1):
            print(f"  {i:2}. {cmd:<15} {desc}")

        print("  " + "─" * 50)

        try:
            choice = input("  Enter number or command (Enter to cancel): ").strip()

            if not choice:
                return None
            
            # Check if it's a number
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    return items[idx][0]
            
            # Check if it's a direct command match
            for cmd, _ in items:
                if cmd == choice:
                    return cmd
            
            # Check if it's a partial match
            matches = [cmd for cmd, _ in items if cmd.startswith(choice)]
            if len(matches) == 1:
                return matches[0]
            
            print(f"  [Invalid selection: {choice}]")
            return None

        except (EOFError, KeyboardInterrupt):
            return None

    def complete(self, text: str) -> str | None:
        """Show menu and return selected command."""
        if not text.startswith("/"):
            return None

        return self.show_menu(text)


class CommandCompleter:
    """Provides tab completion for CLI commands."""

    COMMANDS = [cmd for cmd, _ in InteractiveMenu.COMMANDS]

    def __init__(self):
        self._commands = self.COMMANDS
        self._menu = InteractiveMenu()

    def complete(self, text: str) -> str | None:
        """Show interactive menu for command selection."""
        if text == "/":
            return self._menu.show_menu("")
        elif text.startswith("/"):
            matches = [c for c in self._commands if c.startswith(text)]
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                return self._menu.show_menu(text)
        return None

    def get_matches(self, text: str) -> list[str]:
        """Get all commands matching the text."""
        if text.startswith("/"):
            return [c for c in self._commands if c.startswith(text)]
        return []


def _setup_readline():
    """Setup readline for proper line editing support."""
    # Enable readline features
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set editing-mode emacs")

    # Set history file
    histfile = Path.home() / ".config" / "plan-agent" / ".history"
    histfile.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass

    import atexit

    atexit.register(readline.write_history_file, histfile)


def get_input_with_menu(prompt: str = "> ") -> str:
    """Get input with interactive menu support.

    Uses standard input with readline support for proper line editing
    (arrow keys, Ctrl+Backspace, etc.). Shows menu when user types 
    '/' and presses Enter.
    """
    _setup_readline()
    completer = CommandCompleter()

    print(f"\033[96m{prompt}\033[0m", end="", flush=True)

    try:
        line = input()

        # Check if user just typed "/" - show full menu
        if line.strip() == "/":
            result = completer.complete("/")
            if result:
                return result
            return "/"

        # Check if user typed "/" followed by partial command
        if line.startswith("/") and len(line) > 1:
            result = completer.complete(line)
            if result:
                return result
            return line

        return line
    except EOFError:
        return "/exit"
    except KeyboardInterrupt:
        return ""
