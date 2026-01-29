"""Artifact generation and management for Planning Agent.

Handles saving plans as markdown files, computing diffs between versions,
and displaying artifacts in formatted tables.
"""

import os
import re
from datetime import datetime
from pathlib import Path

# Use user's preferred location: ~/.local/share/plan-agent/artifacts/
ARTIFACTS_DIR = Path.home() / ".local" / "share" / "plan-agent" / "artifacts"


def ensure_artifacts_dir():
    """Create artifacts directory if it doesn't exist."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str | None) -> str:
    """Convert a plan title to a safe filename.

    Args:
        name: Original plan title (may be None)

    Returns:
        Safe filename string (lowercase, no special chars)
    """
    if not name:
        return "untitled"
    # Replace unsafe characters with underscores
    safe = re.sub(r'[^\w\s-]', '_', name)
    # Replace spaces with underscores
    safe = re.sub(r'\s+', '_', safe)
    # Remove multiple consecutive underscores
    safe = re.sub(r'_+', '_', safe)
    return safe.lower().strip('_')[:50]  # Limit length


def find_plan_file(plan_title: str) -> Path | None:
    """Find existing plan file by title."""
    safe_title = sanitize_filename(plan_title)
    pattern = f"{safe_title}.md"

    for filepath in ARTIFACTS_DIR.glob("*.md"):
        if filepath.name == pattern or filepath.name.startswith(f"{safe_title}_"):
            return filepath
    return None


def generate_plan_markdown(plan: dict, old_plan: dict | None = None) -> str:
    """Generate markdown for a plan, with optional diff against old version."""
    lines = [
        f"# {plan.get('title', 'Untitled Plan')}",
        "",
        f"**Version:** {plan.get('version', 1)}",
        f"**Created:** {plan.get('created_at', datetime.now().isoformat())}",
        f"**Updated:** {plan.get('updated_at', datetime.now().isoformat())}",
        "",
        "## Steps",
        "",
    ]

    for step in plan.get("steps", []):
        status_icon = "[x]" if step.get("status") == "completed" else "[ ]"
        desc = step["description"]
        lines.append(f"- {status_icon} **Step {step['id']}:** {desc}")

    history = plan.get("history", [])
    if history and history[-1].get("changes"):
        lines.extend(["", "## Recent Changes", ""])
        for change in history[-1].get("changes", [])[:10]:
            lines.append(f"- {change}")
    # This adds the complete history.
    if history:
        lines.extend(["", "## Version History", ""])
        for entry in history[-5:]:
            ver = entry.get("version", "?")
            ts = entry.get("timestamp", "unknown")[:10]
            lines.append(f"### v{ver} - {ts}")
            for change in entry.get("changes", [])[:5]:
                lines.append(f"- {change}")
            lines.append("")

    lines.append("")
    return "\n".join(lines)


def compute_diff(old_plan: dict | None, new_plan: dict) -> list[tuple[str, str, str]]:
    """
    Compute diff between old and new plan.
    Returns list of (action, old_text, new_text) tuples.
    Action can be: 'add', 'remove', 'modify', 'same', 'title'
    """
    diff = []

    if old_plan:
        old_title = old_plan.get("title", "Untitled")
        new_title = new_plan.get("title", "Untitled")
        if old_title != new_title:
            diff.append(("title", old_title, new_title))

    if not old_plan:
        return [("add", "", step["description"]) for step in new_plan.get("steps", [])]

    old_steps = {s["id"]: s for s in old_plan.get("steps", [])}
    new_steps = {s["id"]: s for s in new_plan.get("steps", [])}

    all_ids = sorted(set(old_steps.keys()) | set(new_steps.keys()))

    for step_id in all_ids:
        if step_id in old_steps and step_id in new_steps:
            old_desc = old_steps[step_id]["description"]
            new_desc = new_steps[step_id]["description"]
            if old_desc != new_desc:
                diff.append(("modify", old_desc, new_desc))
            else:
                diff.append(("same", old_desc, new_desc))
        elif step_id in new_steps:
            diff.append(("add", "", new_steps[step_id]["description"]))
        else:
            diff.append(("remove", old_steps[step_id]["description"], ""))

    return diff


def format_diff_for_display(diff: list[tuple[str, str, str]], max_items: int = 20) -> str:
    """Format diff for CLI display in Claude Code style."""
    lines = []
    for action, old, new in diff[:max_items]:
        if action == "title":
            lines.append(f"TITLE: {old} -> {new}")
        elif action == "add":
            lines.append(f"+ {new}")
        elif action == "remove":
            lines.append(f"- {old}")
        elif action == "modify":
            lines.append(f"- {old}")
            lines.append(f"+ {new}")

    return "\n".join(lines)


def save_plan_artifact(plan: dict, show_diff: bool = True):
    """Save a plan as a markdown artifact.

    Args:
        plan: Plan dictionary to save
        show_diff: Whether to compute diff with previous version

    Returns:
        Tuple of (filepath, diff) where diff may be None
    """
    ensure_artifacts_dir()
    title = sanitize_filename(plan.get("title") or "untitled")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{title}_v{plan.get('version', 1)}_{timestamp}.md"
    filepath = ARTIFACTS_DIR / filename
    old_plan = None
    if filepath.exists():
        old_plan = parse_plan_from_markdown(filepath.read_text())
    diff = compute_diff(old_plan, plan) if old_plan else None
    content = generate_plan_markdown(plan, old_plan)
    filepath.write_text(content)
    return filepath, diff


def parse_plan_from_markdown(content: str) -> dict | None:
    """Parse a plan from markdown content (basic implementation)."""
    lines = content.split("\n")
    plan = {"steps": [], "version": 1, "title": "Unknown"}

    in_steps = False
    for line in lines:
        if line.startswith("# "):
            plan["title"] = line[2:].strip()
        elif "**Version:**" in line:
            try:
                plan["version"] = int(line.split("**Version:**")[1].strip())
            except ValueError:
                pass
        elif line.strip() == "## Steps":
            in_steps = True
        elif in_steps:
            if line.startswith("- ["):
                match = re.match(r"- \[(.)\] \*\*Step (\d+):\*\* (.+)", line)
                if match:
                    status = "completed" if match.group(1) == "x" else "pending"
                    step_id = int(match.group(2))
                    description = match.group(3)
                    plan["steps"].append(
                        {"id": step_id, "description": description, "status": status}
                    )
            elif line.startswith("## "):
                in_steps = False

    return plan if plan["steps"] else None


def create_custom_artifact(name: str, content: str, plan_id: str | None = None) -> Path:
    """Create a custom artifact file.

    Args:
        name: Artifact name
        content: Content to write
        plan_id: Optional associated plan ID

    Returns:
        Path to created artifact file
    """
    ensure_artifacts_dir()

    safe_name = sanitize_filename(name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_name}_{timestamp}.md"
    filepath = ARTIFACTS_DIR / filename

    header = f"""# {name}

**Created:** {datetime.now().isoformat()}
**Plan ID:** {plan_id or "None"}

---

"""

    filepath.write_text(header + content)
    return filepath


def list_artifacts() -> list[dict]:
    """List all saved artifacts.

    Returns:
        List of artifact metadata dictionaries
    """
    ensure_artifacts_dir()

    artifacts = []
    for filepath in sorted(
        ARTIFACTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        stat = filepath.stat()
        artifacts.append(
            {
                "name": filepath.stem,
                "filename": filepath.name,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size,
                "path": filepath,
            }
        )

    return artifacts


def display_artifacts():
    """Display artifacts in a formatted table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    artifacts = list_artifacts()

    if not artifacts:
        console.print("[dim]No artifacts found.[/dim]")
        return

    table = Table(title="Artifacts")
    table.add_column("Name", style="cyan")
    table.add_column("Created", style="dim")
    table.add_column("Size", style="dim", justify="right")

    for art in artifacts[:20]:
        size_kb = art["size"] / 1024
        table.add_row(art["name"][:40], art["created"][:16].replace("T", " "), f"{size_kb:.1f} KB")

    console.print(table)


def diff_artifacts(file1: str, file2: str | None = None) -> list[tuple[str, str, str]] | None:
    """Compute diff between two artifact files.

    Args:
        file1: First artifact filename or path
        file2: Second artifact filename or path (if None, compares with previous version)

    Returns:
        List of diff tuples (action, old, new) or None if files not found
    """
    ensure_artifacts_dir()

    # Resolve file paths
    path1 = ARTIFACTS_DIR / file1 if not Path(file1).is_absolute() else Path(file1)
    if not path1.exists():
        return None

    plan1 = parse_plan_from_markdown(path1.read_text())
    if not plan1:
        return None

    # If file2 not specified, try to find previous version
    if file2 is None:
        # Look for files with same base name pattern
        base_name = path1.stem.rsplit("_v", 1)[0] if "_v" in path1.stem else path1.stem
        versions = sorted(
            [f for f in ARTIFACTS_DIR.glob(f"{base_name}*.md") if f != path1],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not versions:
            return None
        path2 = versions[0]
    else:
        path2 = ARTIFACTS_DIR / file2 if not Path(file2).is_absolute() else Path(file2)
        if not path2.exists():
            return None

    plan2 = parse_plan_from_markdown(path2.read_text())
    if not plan2:
        return None

    # Return diff from older to newer (plan2 is newer)
    if path2.stat().st_mtime > path1.stat().st_mtime:
        return compute_diff(plan1, plan2)
    else:
        return compute_diff(plan2, plan1)


def get_artifact_path(filename: str) -> Path | None:
    """Get full path to an artifact file.

    Args:
        filename: Artifact filename

    Returns:
        Full path to artifact or None if not found
    """
    ensure_artifacts_dir()
    path = ARTIFACTS_DIR / filename
    return path if path.exists() else None
