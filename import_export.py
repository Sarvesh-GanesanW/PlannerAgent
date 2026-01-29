"""Import and export functionality for various formats."""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol


class ExportFormat:
    """Base class for export formats."""

    def export(self, plan: dict[str, Any]) -> str:
        """Export plan to this format.

        Args:
            plan: Plan dictionary to export

        Returns:
            String content in the target format
        """
        raise NotImplementedError

    def get_extension(self) -> str:
        """Get file extension for this format.

        Returns:
            File extension string (e.g., 'md', 'json')
        """
        raise NotImplementedError


class MarkdownExporter(ExportFormat):
    """Export plan to Markdown format."""

    def export(self, plan: dict[str, Any]) -> str:
        """Export plan to Markdown format."""
        lines = [
            f"# {plan.get('title', 'Untitled Plan')}",
            "",
            f"**Version:** {plan.get('version', 1)}  ",
            f"**Created:** {plan.get('created_at', 'Unknown')}  ",
            f"**Updated:** {plan.get('updated_at', 'Unknown')}",
            "",
        ]

        metadata = plan.get("metadata", {})
        if metadata.get("estimated_duration"):
            lines.append(f"**Estimated Duration:** {metadata['estimated_duration']}  ")

        lines.append("")

        deps = metadata.get("dependencies", {})
        milestones = set(metadata.get("milestones", []))

        lines.append("## Steps")
        lines.append("")

        for step in plan.get("steps", []):
            status = step.get("status", "pending")
            icon = "✅" if status == "completed" else "⬜"
            milestone_icon = " 🏁" if step["id"] in milestones else ""

            lines.append(f"{icon} **Step {step['id']}:**{milestone_icon} {step['description']}")

            if "due_date" in step:
                lines.append(f"   📅 Due: {step['due_date'][:10]}")

            if "estimated_hours" in step:
                lines.append(f"   ⏱️ Estimated: {step['estimated_hours']} hours")

            step_deps = deps.get(str(step["id"]), [])
            if step_deps:
                lines.append(f"   🔗 Depends on: {', '.join(map(str, step_deps))}")

            if "sub_steps" in step:
                for sub in step["sub_steps"]:
                    sub_icon = "✓" if sub.get("status") == "completed" else "○"
                    lines.append(f"      {sub_icon} {sub['description']}")

        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(plan.get("summary", "No summary available"))

        if plan.get("history"):
            lines.append("")
            lines.append("## History")
            lines.append("")
            for entry in plan["history"][-5:]:
                lines.append(f"- v{entry.get('version', '?')} - {entry.get('action', 'unknown')}")

        return "\n".join(lines)

    def get_extension(self) -> str:
        """Get file extension."""
        return "md"


class JSONExporter(ExportFormat):
    """Export plan to JSON format."""

    def export(self, plan: dict[str, Any]) -> str:
        """Export plan to JSON format."""
        return json.dumps(plan, indent=2, default=str)

    def get_extension(self) -> str:
        """Get file extension."""
        return "json"


class HTMLExporter(ExportFormat):
    """Export plan to HTML format."""

    def export(self, plan: dict[str, Any]) -> str:
        """Export plan to HTML format."""
        title = plan.get("title", "Untitled Plan")
        steps = plan.get("steps", [])
        metadata = plan.get("metadata", {})
        milestones = set(metadata.get("milestones", []))

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        .metadata {{ color: #666; margin: 20px 0; }}
        .step {{ margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        .step.completed {{ background: #d4edda; }}
        .step.milestone {{ border-left: 4px solid #007bff; }}
        .step-number {{ font-weight: bold; color: #007bff; }}
        .status {{ float: right; }}
        .due-date {{ color: #dc3545; font-size: 0.9em; }}
        .estimate {{ color: #28a745; font-size: 0.9em; }}
        .dependencies {{ color: #6c757d; font-size: 0.9em; }}
        .sub-steps {{ margin-left: 30px; margin-top: 10px; }}
        .sub-step {{ padding: 5px 0; }}
        h2 {{ color: #555; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>📋 {title}</h1>
    <div class="metadata">
        <p><strong>Version:</strong> {plan.get("version", 1)}</p>
        <p><strong>Created:</strong> {plan.get("created_at", "Unknown")[:10]}</p>
        <p><strong>Updated:</strong> {plan.get("updated_at", "Unknown")[:10]}</p>
    </div>
    <h2>Steps</h2>
"""

        for step in steps:
            status = step.get("status", "pending")
            is_completed = status == "completed"
            is_milestone = step["id"] in milestones
            css_class = "step"
            if is_completed:
                css_class += " completed"
            if is_milestone:
                css_class += " milestone"

            status_icon = "✅" if is_completed else "⬜"
            milestone_badge = " 🏁 Milestone" if is_milestone else ""

            html += f'    <div class="{css_class}">\n'
            html += f'        <span class="status">{status_icon}</span>\n'
            html += (
                f'        <span class="step-number">Step {step["id"]}</span>{milestone_badge}<br>\n'
            )
            html += f"        <strong>{step['description']}</strong>\n"

            if "due_date" in step:
                html += f'        <div class="due-date">📅 Due: {step["due_date"][:10]}</div>\n'

            if "estimated_hours" in step:
                html += f'        <div class="estimate">⏱️ Estimated: {step["estimated_hours"]} hours</div>\n'

            deps = metadata.get("dependencies", {}).get(str(step["id"]), [])
            if deps:
                html += f'        <div class="dependencies">🔗 Depends on steps: {", ".join(map(str, deps))}</div>\n'

            if "sub_steps" in step:
                html += '        <div class="sub-steps">\n'
                for sub in step["sub_steps"]:
                    sub_icon = "✓" if sub.get("status") == "completed" else "○"
                    html += (
                        f'            <div class="sub-step">{sub_icon} {sub["description"]}</div>\n'
                    )
                html += "        </div>\n"

            html += "    </div>\n"

        html += (
            """    <h2>Summary</h2>
    <p>"""
            + plan.get("summary", "No summary available").replace("\n", "<br>")
            + """</p>
</body>
</html>"""
        )

        return html

    def get_extension(self) -> str:
        """Get file extension."""
        return "html"


class CSVExporter(ExportFormat):
    """Export plan to CSV format."""

    def export(self, plan: dict[str, Any]) -> str:
        """Export plan to CSV format."""
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            ["Step ID", "Description", "Status", "Due Date", "Estimated Hours", "Is Milestone"]
        )

        metadata = plan.get("metadata", {})
        milestones = set(metadata.get("milestones", []))

        for step in plan.get("steps", []):
            writer.writerow(
                [
                    step["id"],
                    step["description"],
                    step.get("status", "pending"),
                    step.get("due_date", ""),
                    step.get("estimated_hours", ""),
                    "Yes" if step["id"] in milestones else "No",
                ]
            )

        return output.getvalue()

    def get_extension(self) -> str:
        """Get file extension."""
        return "csv"


class PDFExporter:
    """Export plan to PDF (returns HTML that can be printed to PDF)."""

    def export(self, plan: dict[str, Any]) -> str:
        """Export plan to PDF-compatible HTML."""
        html_exporter = HTMLExporter()
        html = html_exporter.export(plan)

        print_styles = """
        <style>
            @media print {
                body { margin: 0; padding: 20px; }
                .step { page-break-inside: avoid; }
                h1 { page-break-after: avoid; }
            }
        </style>
        """

        return html.replace("</head>", f"{print_styles}</head>")

    def get_extension(self) -> str:
        """Get file extension."""
        return "html"


class ImportParser(Protocol):
    """Protocol for import parsers."""

    def parse(self, content: str) -> dict[str, Any] | None:
        """Parse content and return plan dictionary."""
        ...

    def can_parse(self, content: str) -> bool:
        """Check if this parser can handle the given content."""
        ...


class TrelloJsonImporter:
    """Import from Trello board JSON export."""

    def parse(self, content: str) -> dict[str, Any] | None:
        """Parse Trello JSON export into plan format."""
        try:
            data = json.loads(content)

            cards = data.get("cards", [])
            lists = {lst["id"]: lst["name"] for lst in data.get("lists", [])}

            timestamp = datetime.now().isoformat()

            steps = []
            for i, card in enumerate(cards):
                if not card.get("closed", False):
                    steps.append(
                        {
                            "id": i + 1,
                            "description": f"[{lists.get(card.get('idList'), 'Unknown')}] {card['name']}",
                            "status": "completed" if card.get("dueComplete") else "pending",
                            "created_at": timestamp,
                        }
                    )

            return {
                "title": data.get("name", "Imported Trello Board"),
                "steps": steps,
                "version": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
                "history": [
                    {
                        "version": 1,
                        "timestamp": timestamp,
                        "action": "imported",
                        "title": data.get("name", "Imported Trello Board"),
                        "steps": steps,
                    }
                ],
                "summary": f"Imported from Trello: {len(steps)} cards",
                "metadata": {
                    "total_steps": len(steps),
                    "completed_steps": sum(1 for s in steps if s["status"] == "completed"),
                    "status": "draft",
                    "source": "trello",
                },
            }
        except (json.JSONDecodeError, KeyError):
            return None

    def can_parse(self, content: str) -> bool:
        """Check if content is Trello JSON format."""
        try:
            data = json.loads(content)
            return "cards" in data and "lists" in data
        except json.JSONDecodeError:
            return False


class CSVImporter:
    """Import from CSV format."""

    def parse(self, content: str) -> dict[str, Any] | None:
        """Parse CSV content into plan format."""
        try:
            import io

            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)

            if not rows:
                return None

            timestamp = datetime.now().isoformat()
            steps = []

            for i, row in enumerate(rows):
                step = {
                    "id": i + 1,
                    "description": row.get("Description", row.get("description", f"Step {i + 1}")),
                    "status": row.get("Status", row.get("status", "pending")).lower(),
                    "created_at": timestamp,
                }

                if "Due Date" in row or "due_date" in row:
                    step["due_date"] = row.get("Due Date", row.get("due_date", ""))

                steps.append(step)

            return {
                "title": "Imported CSV Plan",
                "steps": steps,
                "version": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
                "history": [
                    {
                        "version": 1,
                        "timestamp": timestamp,
                        "action": "imported",
                        "title": "Imported CSV Plan",
                        "steps": steps,
                    }
                ],
                "summary": f"Imported from CSV: {len(steps)} steps",
                "metadata": {
                    "total_steps": len(steps),
                    "completed_steps": sum(1 for s in steps if s["status"] == "completed"),
                    "status": "draft",
                    "source": "csv",
                },
            }
        except Exception:
            return None

    def can_parse(self, content: str) -> bool:
        """Check if content is CSV format."""
        lines = content.strip().split("\n")
        if len(lines) < 2:
            return False

        header = lines[0].lower()
        return "description" in header or "step" in header


class MarkdownImporter:
    """Import from Markdown format."""

    def parse(self, content: str) -> dict[str, Any] | None:
        """Parse Markdown content into plan format."""
        lines = content.split("\n")

        title = "Imported Markdown Plan"
        steps = []
        timestamp = datetime.now().isoformat()

        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()

            match = re.match(r"[-*]\s*\[(.|x|X|\s)\]\s*\*\*Step\s*(\d+):\*\*\s*(.+)", line)
            if match:
                status_char = match.group(1).lower()
                step_id = int(match.group(2))
                description = match.group(3).strip()

                status = "completed" if status_char in ["x", "✅"] else "pending"

                steps.append(
                    {
                        "id": step_id,
                        "description": description,
                        "status": status,
                        "created_at": timestamp,
                    }
                )

        if not steps:
            for i, line in enumerate(lines):
                match = re.match(r"[-*]\s*\[(.|x|X|\s)\]\s*(.+)", line)
                if match:
                    status_char = match.group(1).lower()
                    description = match.group(2).strip()

                    if not description.startswith("**"):
                        status = "completed" if status_char in ["x", "✅"] else "pending"
                        steps.append(
                            {
                                "id": len(steps) + 1,
                                "description": description,
                                "status": status,
                                "created_at": timestamp,
                            }
                        )

        if not steps:
            return None

        return {
            "title": title,
            "steps": steps,
            "version": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
            "history": [
                {
                    "version": 1,
                    "timestamp": timestamp,
                    "action": "imported",
                    "title": title,
                    "steps": steps,
                }
            ],
            "summary": f"Imported from Markdown: {len(steps)} steps",
            "metadata": {
                "total_steps": len(steps),
                "completed_steps": sum(1 for s in steps if s["status"] == "completed"),
                "status": "draft",
                "source": "markdown",
            },
        }

    def can_parse(self, content: str) -> bool:
        """Check if content is Markdown checklist format."""
        lines = content.split("\n")
        checkbox_pattern = re.compile(r"[-*]\s*\[.\]")

        for line in lines:
            if checkbox_pattern.search(line):
                return True

        return False


class ExportManager:
    """Manages all export operations."""

    def __init__(self):
        self._exporters = {
            "markdown": MarkdownExporter(),
            "md": MarkdownExporter(),
            "json": JSONExporter(),
            "html": HTMLExporter(),
            "csv": CSVExporter(),
            "pdf": PDFExporter(),
        }

    def export(self, plan: dict[str, Any], format: str) -> str:
        """Export plan to specified format."""
        exporter = self._exporters.get(format.lower())
        if not exporter:
            available = ", ".join(self._exporters.keys())
            raise ValueError(f"Unknown format: {format}. Available: {available}")

        return exporter.export(plan)

    def get_extension(self, format: str) -> str:
        """Get file extension for format."""
        exporter = self._exporters.get(format.lower())
        if exporter:
            return exporter.get_extension()
        return "txt"

    def get_available_formats(self) -> list[str]:
        """Get list of available export formats."""
        return list(self._exporters.keys())


class ImportManager:
    """Manages all import operations."""

    def __init__(self):
        self._importers = [
            TrelloJsonImporter(),
            CSVImporter(),
            MarkdownImporter(),
        ]

    def import_plan(self, content: str, format_hint: str | None = None) -> dict[str, Any] | None:
        """Import plan from content, auto-detecting format."""
        if format_hint:
            for importer in self._importers:
                if importer.__class__.__name__.lower().startswith(format_hint.lower()):
                    return importer.parse(content)

        for importer in self._importers:
            if importer.can_parse(content):
                return importer.parse(content)

        return None

    def detect_format(self, content: str) -> str | None:
        """Detect the format of the content."""
        for importer in self._importers:
            if importer.can_parse(content):
                return importer.__class__.__name__.replace("Importer", "").lower()
        return None


def export_plan_to_file(plan: dict[str, Any], format: str, filepath: str | None = None) -> str:
    """Export plan to a file and return the filepath."""
    manager = ExportManager()
    content = manager.export(plan, format)

    if not filepath:
        from artifacts import sanitize_filename

        base_name = sanitize_filename(plan.get("title", "plan"))
        extension = manager.get_extension(format)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"artifacts/{base_name}_{timestamp}.{extension}"

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text(content)

    return filepath


def import_plan_from_file(filepath: str) -> dict[str, Any] | None:
    """Import plan from a file."""
    path = Path(filepath)
    if not path.exists():
        return None

    content = path.read_text()
    manager = ImportManager()

    format_hint = path.suffix.lstrip(".").lower()
    return manager.import_plan(content, format_hint)
