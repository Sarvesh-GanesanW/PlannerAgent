"""Gantt chart generation for plans."""

from datetime import datetime, timedelta
from typing import Any


class GanttChartGenerator:
    """Generate Gantt charts from plans."""

    def __init__(self, plan: dict[str, Any]):
        self._plan = plan
        self._steps = plan.get("steps", [])
        self._metadata = plan.get("metadata", {})
        self._dependencies = self._metadata.get("dependencies", {})

    def generate_html(self) -> str:
        """Generate an interactive HTML Gantt chart."""
        if not self._steps:
            return "<p>No steps to display</p>"

        dates = self._calculate_dates()
        total_days = self._get_total_days(dates)
        milestones = set(self._metadata.get("milestones", []))

        html = self._generate_html_header()
        html += self._generate_timeline_header(dates)
        html += self._generate_step_rows(dates, total_days, milestones)
        html += self._generate_html_footer()

        return html

    def generate_svg(self) -> str:
        """Generate an SVG Gantt chart."""
        if not self._steps:
            return "<svg></svg>"

        dates = self._calculate_dates()
        total_days = self._get_total_days(dates)

        width = max(800, total_days * 40 + 200)
        height = len(self._steps) * 40 + 100

        svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        svg += '<rect width="100%" height="100%" fill="#f8f9fa"/>'

        # Title
        title = self._plan.get("title", "Plan")
        svg += f'<text x="20" y="30" font-size="20" font-weight="bold" fill="#333">{title}</text>'

        # Timeline header
        svg += self._generate_svg_timeline(dates, total_days)

        # Steps
        milestones = set(self._metadata.get("milestones", []))
        for i, step in enumerate(self._steps):
            y = 80 + i * 35
            svg += self._generate_svg_step_bar(step, dates, total_days, y, width, milestones)

        svg += "</svg>"
        return svg

    def _calculate_dates(self) -> dict[int, datetime]:
        """Calculate start dates for each step based on dependencies."""
        dates = {}
        start_date = datetime.now()

        # Sort steps respecting dependencies
        sorted_steps = self._topological_sort()

        for step in sorted_steps:
            step_id = step["id"]
            deps = self._dependencies.get(str(step_id), [])

            if deps:
                latest_end = max(
                    (
                        dates.get(d, start_date) + timedelta(days=self._get_step_duration(d))
                        for d in deps
                    ),
                    default=start_date,
                )
                dates[step_id] = latest_end + timedelta(days=1)
            else:
                dates[step_id] = start_date

        return dates

    def _topological_sort(self) -> list[dict[str, Any]]:
        """Sort steps based on dependencies."""
        step_map = {s["id"]: s for s in self._steps}
        in_degree = {s["id"]: 0 for s in self._steps}

        for step_id, deps in self._dependencies.items():
            for dep in deps:
                if int(step_id) in in_degree:
                    in_degree[int(step_id)] += 1

        queue = [s for s in self._steps if in_degree[s["id"]] == 0]
        result = []

        while queue:
            step = queue.pop(0)
            result.append(step)

            for step_id, deps in self._dependencies.items():
                if step["id"] in deps:
                    in_degree[int(step_id)] -= 1
                    if in_degree[int(step_id)] == 0:
                        queue.append(step_map[int(step_id)])

        for step in self._steps:
            if step not in result:
                result.append(step)

        return result

    def _get_step_duration(self, step_id: int) -> int:
        """Get duration for a step in days."""
        for step in self._steps:
            if step["id"] == step_id:
                hours = step.get("estimated_hours", 8)
                return max(1, hours // 8)
        return 1

    def _get_total_days(self, dates: dict[int, datetime]) -> int:
        """Calculate total timeline span."""
        if not dates:
            return 30

        min_date = min(dates.values())
        max_date = max(
            dates[s["id"]] + timedelta(days=self._get_step_duration(s["id"])) for s in self._steps
        )
        return max(30, (max_date - min_date).days + 5)

    def _generate_html_header(self) -> str:
        """Generate HTML header with styles."""
        title = self._plan.get("title", "Plan")
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Gantt Chart - {title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 5px; }}
        .header .meta {{ opacity: 0.9; font-size: 14px; }}
        .gantt {{ display: flex; min-height: 400px; }}
        .step-labels {{ width: 250px; background: #f8f9fa; border-right: 1px solid #e0e0e0; padding: 40px 0 0 0; }}
        .step-label {{ height: 40px; padding: 10px 15px; font-size: 13px; border-bottom: 1px solid #e0e0e0; display: flex; align-items: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .step-label.milestone {{ font-weight: bold; background: #fff3cd; }}
        .step-label.completed {{ text-decoration: line-through; opacity: 0.6; }}
        .timeline-container {{ flex: 1; overflow-x: auto; position: relative; }}
        .timeline-header {{ height: 40px; background: #f8f9fa; border-bottom: 1px solid #e0e0e0; display: flex; position: sticky; top: 0; z-index: 10; }}
        .day-header {{ min-width: 40px; text-align: center; padding: 10px 5px; font-size: 11px; color: #666; border-right: 1px solid #e0e0e0; }}
        .day-header.weekend {{ background: #e9ecef; }}
        .timeline-body {{ position: relative; }}
        .step-row {{ height: 40px; border-bottom: 1px solid #e0e0e0; position: relative; }}
        .step-bar {{ position: absolute; height: 24px; top: 8px; border-radius: 4px; display: flex; align-items: center; padding: 0 8px; font-size: 11px; color: white; font-weight: 500; box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: transform 0.2s; }}
        .step-bar:hover {{ transform: translateY(-2px); box-shadow: 0 3px 8px rgba(0,0,0,0.3); }}
        .step-bar.pending {{ background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); }}
        .step-bar.completed {{ background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%); }}
        .step-bar.milestone {{ background: linear-gradient(90deg, #fa709a 0%, #fee140 100%); height: 28px; top: 6px; border-radius: 14px; }}
        .dependency-line {{ position: absolute; border-left: 2px dashed #adb5bd; z-index: 1; }}
        .today-marker {{ position: absolute; top: 0; bottom: 0; width: 2px; background: #dc3545; z-index: 5; }}
        .legend {{ padding: 15px 20px; background: #f8f9fa; border-top: 1px solid #e0e0e0; display: flex; gap: 20px; font-size: 12px; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; }}
        .legend-color {{ width: 20px; height: 12px; border-radius: 2px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {title}</h1>
            <div class="meta">{len(self._steps)} steps • Generated {datetime.now().strftime("%Y-%m-%d")}</div>
        </div>
        <div class="gantt">
            <div class="step-labels">
"""

    def _generate_timeline_header(self, dates: dict[int, datetime]) -> str:
        """Generate the timeline header with days."""
        total_days = self._get_total_days(dates)
        min_date = min(dates.values()) if dates else datetime.now()

        html = ""
        for step in self._steps:
            is_milestone = step["id"] in self._metadata.get("milestones", [])
            is_completed = step.get("status") == "completed"
            css_class = ""
            if is_milestone:
                css_class += " milestone"
            if is_completed:
                css_class += " completed"

            html += f'<div class="step-label{css_class}">{step["id"]}. {step["description"][:35]}</div>\n'

        html += '</div>\n<div class="timeline-container">\n<div class="timeline-header">\n'

        for day in range(total_days):
            date = min_date + timedelta(days=day)
            is_weekend = date.weekday() >= 5
            day_class = "day-header weekend" if is_weekend else "day-header"
            html += f'<div class="{day_class}">{date.strftime("%d")}</div>\n'

        html += '</div>\n<div class="timeline-body">\n'
        return html

    def _generate_step_rows(
        self, dates: dict[int, datetime], total_days: int, milestones: set
    ) -> str:
        """Generate the step rows with bars."""
        html = ""
        min_date = min(dates.values()) if dates else datetime.now()

        for step in self._steps:
            step_id = step["id"]
            start_date = dates.get(step_id, min_date)
            duration = self._get_step_duration(step_id)
            days_from_start = (start_date - min_date).days

            left = days_from_start * 40
            width = duration * 40 - 4

            is_milestone = step_id in milestones
            is_completed = step.get("status") == "completed"
            status_class = "completed" if is_completed else "pending"
            if is_milestone:
                status_class = "milestone"

            html += '<div class="step-row">\n'
            html += f'  <div class="step-bar {status_class}" style="left: {left}px; width: {width}px;">\n'

            if is_milestone:
                html += f"    🏁 {step['description'][:20]}\n"
            else:
                html += f"    {step['description'][:20]}\n"

            html += "  </div>\n"

            # Draw dependency lines
            deps = self._dependencies.get(str(step_id), [])
            for dep_id in deps:
                if dep_id in dates:
                    dep_end_date = dates[dep_id] + timedelta(days=self._get_step_duration(dep_id))
                    dep_x = (dep_end_date - min_date).days * 40
                    line_left = dep_x
                    line_height = 40
                    html += f'  <div class="dependency-line" style="left: {line_left}px; top: -20px; height: {line_height}px;"></div>\n'

            html += "</div>\n"

        # Today marker
        today = datetime.now()
        if min_date <= today <= min_date + timedelta(days=total_days):
            today_offset = (today - min_date).days * 40
            html += f'<div class="today-marker" style="left: {today_offset}px;"></div>\n'

        return html

    def _generate_html_footer(self) -> str:
        """Generate HTML footer with legend."""
        return """
            </div>
        </div>
    </div>
    <div class="legend">
        <div class="legend-item">
            <div class="legend-color" style="background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);"></div>
            <span>Pending</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%);"></div>
            <span>Completed</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: linear-gradient(90deg, #fa709a 0%, #fee140 100%);"></div>
            <span>Milestone</span>
        </div>
        <div class="legend-item">
            <div style="width: 2px; height: 12px; background: #dc3545;"></div>
            <span>Today</span>
        </div>
    </div>
</div>
</body>
</html>
"""

    def _generate_svg_timeline(self, dates: dict[int, datetime], total_days: int) -> str:
        """Generate SVG timeline header."""
        min_date = min(dates.values()) if dates else datetime.now()
        svg = ""

        for day in range(total_days):
            date = min_date + timedelta(days=day)
            x = 200 + day * 40
            is_weekend = date.weekday() >= 5
            fill = "#e9ecef" if is_weekend else "#f8f9fa"

            svg += f'<rect x="{x}" y="40" width="40" height="30" fill="{fill}" stroke="#e0e0e0"/>'
            svg += f'<text x="{x + 20}" y="60" text-anchor="middle" font-size="10" fill="#666">{date.strftime("%d")}</text>'

        return svg

    def _generate_svg_step_bar(
        self,
        step: dict[str, Any],
        dates: dict[int, datetime],
        total_days: int,
        y: int,
        width: int,
        milestones: set,
    ) -> str:
        """Generate SVG bar for a step."""
        step_id = step["id"]
        min_date = min(dates.values()) if dates else datetime.now()
        start_date = dates.get(step_id, min_date)
        duration = self._get_step_duration(step_id)
        days_from_start = (start_date - min_date).days

        x = 200 + days_from_start * 40
        bar_width = duration * 40 - 4

        is_milestone = step_id in milestones
        is_completed = step.get("status") == "completed"

        if is_completed:
            fill = "#43e97b"
        elif is_milestone:
            fill = "#fa709a"
        else:
            fill = "#4facfe"

        svg = ""

        # Step label
        svg += f'<text x="10" y="{y + 20}" font-size="12" fill="#333">{step_id}. {step["description"][:30]}</text>'

        # Bar
        height = 24 if not is_milestone else 28
        bar_y = y + (30 - height) // 2
        rx = 14 if is_milestone else 4

        svg += f'<rect x="{x}" y="{bar_y}" width="{bar_width}" height="{height}" fill="{fill}" rx="{rx}"/>'

        if bar_width > 60:
            text_color = "white"
            label = "🏁" if is_milestone else step["description"][:15]
            svg += f'<text x="{x + 8}" y="{bar_y + height // 2 + 4}" font-size="10" fill="{text_color}">{label}</text>'

        return svg


def export_gantt_chart(plan: dict[str, Any], format: str = "html") -> str:
    """Export a Gantt chart for the plan.

    Args:
        plan: The plan dictionary
        format: Export format (html or svg)

    Returns:
        The chart content as string
    """
    generator = GanttChartGenerator(plan)

    if format == "html":
        return generator.generate_html()
    elif format == "svg":
        return generator.generate_svg()
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'html' or 'svg'.")
