"""Core planning tools for the Planning Agent.

Provides tools for plan creation, modification, analysis, and visualization.
All tools are decorated with @tool for LangChain integration.
"""

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

from langchain_core.tools import tool


@tool
def create_plan(title: str, steps: list[str]) -> dict[str, Any]:
    """Create a new plan with a title and list of steps."""
    timestamp = datetime.now().isoformat()
    plan = {
        "title": title,
        "steps": [
            {"id": i + 1, "description": step, "status": "pending", "created_at": timestamp}
            for i, step in enumerate(steps)
        ],
        "version": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
        "history": [],
        "summary": f"Plan for {title} with {len(steps)} steps.",
        "metadata": {"total_steps": len(steps), "completed_steps": 0, "status": "draft"},
    }
    plan["history"].append(
        {
            "version": 1,
            "timestamp": timestamp,
            "action": "created",
            "title": title,
            "steps": [s.copy() for s in plan["steps"]],
        }
    )
    return plan


@tool
def update_plan(
    current_plan: dict[str, Any],
    modifications: list[dict[str, Any]],
    new_title: str | None = None,
) -> dict[str, Any]:
    """Update an existing plan with modifications.

    IMPORTANT: For "update" and "remove" actions, you MUST provide the "id" field.
    The id is the step number shown in the plan (e.g., id=2 for "Step 2").

    Args:
        current_plan: The current plan to update
        modifications: List of modification actions
        new_title: Optional new title for the plan (use when user wants to rename)

    Example modifications:
    - {"action": "add", "description": "New step description"}
    - {"action": "update", "id": 2, "description": "Updated description"}  # id REQUIRED
    - {"action": "remove", "id": 3}  # id REQUIRED
    - {"action": "reorder", "new_order": [3, 1, 2]}
    """
    if not current_plan:
        raise ValueError("No current plan provided for update")

    timestamp = datetime.now().isoformat()
    updated_plan = {
        "title": new_title if new_title else current_plan.get("title", "Untitled"),
        "steps": [s.copy() for s in current_plan.get("steps", [])],
        "version": current_plan.get("version", 1),
        "created_at": current_plan.get("created_at", timestamp),
        "history": current_plan.get("history", []),
        "metadata": current_plan.get("metadata", {}),
    }

    changes = []

    if new_title and new_title != current_plan.get("title", "Untitled"):
        changes.append(f"Updated title: '{current_plan.get('title', 'Untitled')}' -> '{new_title}'")

    existing_steps = updated_plan["steps"]

    for mod in modifications:
        action = mod.get("action")

        if action == "add":
            new_id = len(existing_steps) + 1
            new_step = {
                "id": new_id,
                "description": mod.get("description", ""),
                "status": mod.get("status", "pending"),
                "created_at": timestamp,
            }
            existing_steps.append(new_step)
            changes.append(f"Added step {new_id}: {new_step['description']}")

        elif action == "update":
            step_id = mod.get("id")

            # Handle missing step_id - try to find by description match
            if step_id is None and "description" in mod:
                target_desc = mod.get("description", "").lower()
                for step in existing_steps:
                    if (
                        target_desc in step["description"].lower()
                        or step["description"].lower() in target_desc
                    ):
                        step_id = step["id"]
                        changes.append(f"Auto-detected step ID {step_id} from description")
                        break

            if step_id is None:
                # Return error with available steps
                available = ", ".join(
                    [f"{s['id']}: {s['description'][:30]}" for s in existing_steps[:5]]
                )
                changes.append(f"ERROR: Missing 'id' for update. Available steps: {available}")
                continue

            found = False
            for step in existing_steps:
                if step["id"] == step_id:
                    old_desc = step["description"]
                    if "description" in mod:
                        step["description"] = mod["description"]
                    if "status" in mod:
                        step["status"] = mod["status"]
                    step["updated_at"] = timestamp
                    if old_desc != step["description"]:
                        changes.append(
                            f"Updated step {step_id}: '{old_desc}' -> '{step['description']}'"
                        )
                    else:
                        changes.append(f"Modified step {step_id}")
                    found = True
                    break
            if not found:
                changes.append(f"Warning: Step {step_id} not found for update")

        elif action == "remove":
            step_id = mod.get("id")

            # Handle missing step_id - try to find by description
            if step_id is None and "description" in mod:
                target_desc = mod.get("description", "").lower()
                for step in existing_steps:
                    if (
                        target_desc in step["description"].lower()
                        or step["description"].lower() in target_desc
                    ):
                        step_id = step["id"]
                        changes.append(f"Auto-detected step ID {step_id} from description")
                        break

            if step_id is None:
                # Return error with available steps
                available = ", ".join(
                    [f"{s['id']}: {s['description'][:30]}" for s in existing_steps[:5]]
                )
                changes.append(f"ERROR: Missing 'id' for removal. Available steps: {available}")
                continue

            original_len = len(existing_steps)
            removed_step = None
            for step in existing_steps:
                if step["id"] == step_id:
                    removed_step = step
                    break
            existing_steps[:] = [s for s in existing_steps if s["id"] != step_id]
            for i, step in enumerate(existing_steps):
                step["id"] = i + 1
            if len(existing_steps) < original_len and removed_step:
                changes.append(f"Removed step {step_id}: {removed_step['description']}")
            else:
                changes.append(f"Warning: Step {step_id} not found for removal")

        elif action == "reorder":
            new_order = mod.get("new_order", [])
            if new_order and len(new_order) == len(existing_steps):
                step_map = {s["id"]: s for s in existing_steps}
                reordered = []
                for new_id in new_order:
                    if new_id in step_map:
                        reordered.append(step_map[new_id])
                for i, step in enumerate(reordered):
                    step["id"] = i + 1
                updated_plan["steps"] = reordered
                changes.append(f"Reordered steps to: {new_order}")

    updated_plan["version"] = current_plan.get("version", 1) + 1
    updated_plan["updated_at"] = timestamp
    updated_plan["history"].append(
        {
            "version": updated_plan["version"],
            "timestamp": timestamp,
            "action": "updated",
            "steps": [s.copy() for s in updated_plan["steps"]],
            "changes": changes,
        }
    )

    completed = sum(1 for s in updated_plan["steps"] if s.get("status") == "completed")
    updated_plan["metadata"] = {
        "total_steps": len(updated_plan["steps"]),
        "completed_steps": completed,
        "status": "completed"
        if completed == len(updated_plan["steps"]) and len(updated_plan["steps"]) > 0
        else "in_progress",
    }

    change_summary = "; ".join(changes) if changes else "Minor updates"
    updated_plan["summary"] = (
        f"Plan '{updated_plan['title']}' v{updated_plan['version']} "
        f"with {len(updated_plan['steps'])} steps ({completed} completed). "
        f"Changes: {change_summary}"
    )

    return updated_plan


@tool
def appknox_security_audit(plan: dict[str, Any]) -> str:
    """Generate security audit recommendations using AppKnox."""
    steps = plan.get("steps", []) if plan else []
    base_id = len(steps) + 1

    sast_step = {
        "id": base_id,
        "description": "Run AppKnox SAST scan to detect static code vulnerabilities",
        "status": "pending",
    }
    dast_step = {
        "id": base_id + 1,
        "description": "Run AppKnox DAST scan to detect runtime vulnerabilities",
        "status": "pending",
    }
    api_step = {
        "id": base_id + 2,
        "description": "Perform API security testing with AppKnox",
        "status": "pending",
    }

    return f"""🔒 Security Audit Recommendation:

Based on your plan, I recommend adding these security steps:

1. Step {sast_step["id"]}: {sast_step["description"]}
2. Step {dast_step["id"]}: {dast_step["description"]}
3. Step {api_step["id"]}: {api_step["description"]}

These steps will help ensure your project is secure before deployment.
Would you like me to add these to your plan?"""


@tool
def generate_plan_summary(plan: dict[str, Any]) -> str:
    """Generate a formatted summary of the current plan."""
    if not plan:
        return "📋 No plan exists yet. Let's create one!"

    title = plan.get("title", "Untitled")
    version = plan.get("version", 1)
    steps = plan.get("steps", [])
    metadata = plan.get("metadata", {})

    completed = metadata.get(
        "completed_steps", sum(1 for s in steps if s.get("status") == "completed")
    )
    total = metadata.get("total_steps", len(steps))

    lines = [
        "",
        "╔" + "═" * 58 + "╗",
        f"║{'📋 PLAN: ' + title[:48]:^58}║",
        f"║{'Version ' + str(version) + ' (' + str(completed) + '/' + str(total) + ' completed)':^58}║",
        "╠" + "═" * 58 + "╣",
    ]

    if not steps:
        lines.append(f"║{'No steps defined yet':^58}║")
    else:
        for step in steps:
            status_icon = "✅" if step.get("status") == "completed" else "⬜"
            desc = (
                step["description"][:50] + "..."
                if len(step["description"]) > 50
                else step["description"]
            )
            line = f"{status_icon} Step {step['id']}: {desc}"
            lines.append(f"║{line:<58}║")

    lines.append("╚" + "═" * 58 + "╝")
    lines.append("")

    return "\n".join(lines)


@tool
def generate_plan_diff(plan: dict[str, Any]) -> str:
    """Generate a diff showing changes between plan versions."""
    if not plan or "history" not in plan or len(plan.get("history", [])) < 2:
        return "📊 No previous version to compare with."

    history = plan["history"]
    if len(history) < 2:
        return "📊 No previous version to compare with."

    old = history[-2]
    new = history[-1]

    old_steps = {s["id"]: s for s in old.get("steps", [])}
    new_steps = {s["id"]: s for s in new.get("steps", [])}
    all_ids = set(old_steps.keys()) | set(new_steps.keys())

    lines = [
        "",
        "╔" + "═" * 58 + "╗",
        f"║{'📊 PLAN CHANGES':^58}║",
        f"║{'v' + str(old['version']) + ' → v' + str(new['version']):^58}║",
        "╠" + "═" * 58 + "╣",
    ]

    has_changes = False
    for step_id in sorted(all_ids):
        if step_id not in old_steps:
            has_changes = True
            desc = new_steps[step_id]["description"][:45]
            lines.append(f"║  ➕ ADDED Step {step_id}: {desc:<35}║")
        elif step_id not in new_steps:
            has_changes = True
            desc = old_steps[step_id]["description"][:42]
            lines.append(f"║  ➖ REMOVED Step {step_id}: {desc:<32}║")
        elif old_steps[step_id]["description"] != new_steps[step_id]["description"]:
            has_changes = True
            lines.append(f"║  📝 MODIFIED Step {step_id}:{'':<38}║")
            old_desc = old_steps[step_id]["description"][:48]
            new_desc = new_steps[step_id]["description"][:48]
            lines.append(f"║     - {old_desc:<50}║")
            lines.append(f"║     + {new_desc:<50}║")

    if not has_changes:
        lines.append(f"║{'  (No structural changes)':<58}║")

    if new.get("changes"):
        lines.append("╠" + "═" * 58 + "╣")
        lines.append(f"║{'Summary of changes:':<58}║")
        for change in new["changes"]:
            for i in range(0, len(change), 54):
                chunk = change[i : i + 54]
                lines.append(f"║  • {chunk:<54}║")

    lines.append("╚" + "═" * 58 + "╝")
    lines.append("")

    return "\n".join(lines)


@tool
def generate_executive_summary(summary: str, plan: dict[str, Any]) -> str:
    """Generate an executive summary of the conversation and plan."""
    lines = [
        "",
        "╔" + "═" * 58 + "╗",
        "║" + "📋 EXECUTIVE SUMMARY".center(58) + "║",
        "╠" + "═" * 58 + "╣",
    ]

    if plan:
        title = plan.get("title", "Untitled")
        version = plan.get("version", 1)
        steps = plan.get("steps", [])
        metadata = plan.get("metadata", {})
        completed = metadata.get("completed_steps", 0)
        total = len(steps)

        lines.append(f"║  📌 Plan: {title[:48]:<48}║")
        lines.append(f"║  🔄 Version: {version:<45}║")
        lines.append(f"║  ✅ Progress: {completed}/{total} steps completed{'':<24}║")

        if completed > 0:
            lines.append("║  ──────────────────────────────────────────────────────  ║")
            lines.append(f"║  {'Completed steps:':<54}║")
            for step in steps:
                if step.get("status") == "completed":
                    desc = step["description"][:45]
                    lines.append(f"║    ✓ {desc:<51}║")
    else:
        lines.append(f"║  📌 No plan created yet{'':<34}║")

    if summary:
        lines.append("╠" + "═" * 58 + "╣")
        lines.append(f"║  {'💬 Conversation Summary:':<54}║")
        words = summary.split()
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= 52:
                current_line += " " + word if current_line else word
            else:
                lines.append(f"║    {current_line:<52}║")
                current_line = word
        if current_line:
            lines.append(f"║    {current_line:<52}║")

    lines.append("╚" + "═" * 58 + "╝")
    lines.append("")

    return "\n".join(lines)


@tool
def detect_ambiguity(user_input: str) -> dict[str, Any]:
    """Detect if a user request is ambiguous and needs clarification."""
    user_input_lower = user_input.lower()

    planning_keywords = ["plan", "build", "create", "make", "organize", "schedule"]
    has_planning_intent = any(kw in user_input_lower for kw in planning_keywords)

    if not has_planning_intent:
        return {"is_ambiguous": False, "questions": []}

    ambiguity_indicators = []
    questions = []

    if len(user_input.split()) < 5:
        ambiguity_indicators.append("too_short")
        questions.append("Could you provide more details about what you want to accomplish?")

    vague_terms = ["something", "anything", "stuff", "things", "it", "that"]
    if any(term in user_input_lower for term in vague_terms):
        ambiguity_indicators.append("vague_terms")
        questions.append("Could you be more specific about what you're referring to?")

    constraint_keywords = ["budget", "time", "deadline", "timeline", "when", "cost", "price"]
    has_constraints = any(kw in user_input_lower for kw in constraint_keywords)

    scope_indicators = ["website", "app", "project", "event", "trip", "product"]
    has_scope = any(kw in user_input_lower for kw in scope_indicators)

    if has_planning_intent and has_scope:
        if "website" in user_input_lower:
            if not any(
                kw in user_input_lower
                for kw in ["e-commerce", "blog", "portfolio", "landing", "type"]
            ):
                questions.append(
                    "What type of website? (e-commerce, blog, portfolio, landing page, etc.)"
                )
            if not any(
                kw in user_input_lower for kw in ["sell", "showcase", "share", "purpose", "goal"]
            ):
                questions.append("What's the main purpose or goal of the website?")

        elif "trip" in user_input_lower or "travel" in user_input_lower:
            if not any(
                kw in user_input_lower
                for kw in ["destination", "where", "place", "country", "city"]
            ):
                questions.append("Where would you like to travel to?")
            if not any(
                kw in user_input_lower for kw in ["when", "date", "duration", "how long", "days"]
            ):
                questions.append("When are you planning to go and for how long?")

        elif "event" in user_input_lower:
            if not any(
                kw in user_input_lower
                for kw in ["type", "wedding", "party", "conference", "meeting"]
            ):
                questions.append("What type of event? (wedding, party, conference, etc.)")
            if not any(kw in user_input_lower for kw in ["guests", "people", "attendees", "size"]):
                questions.append("How many guests are you expecting?")

    if has_planning_intent and not has_constraints and len(user_input.split()) > 3:
        questions.append("Do you have any timeline or budget constraints I should know about?")

    return {
        "is_ambiguous": len(questions) > 0,
        "questions": questions[:3],
        "indicators": ambiguity_indicators,
    }


@tool
def ask_clarifying_question(
    context: str, missing_info: list[str], previous_questions: list[str] | None = None
) -> dict[str, Any]:
    """Generate clarifying questions based on missing information.

    Args:
        context: The conversation context to base questions on
        missing_info: List of information that needs clarification
        previous_questions: Questions already asked to avoid repetition
    """
    previous_questions = previous_questions or []
    # context is used by the LLM for context when this tool is called
    _ = context  # Explicitly mark as used

    new_questions = [q for q in missing_info if q not in previous_questions]

    if not new_questions:
        return {
            "has_questions": False,
            "message": "Thanks for the clarification! Let me proceed with creating your plan.",
        }

    question_text = "To help you better, I need a bit more information:\n\n"
    for i, question in enumerate(new_questions[:3], 1):
        question_text += f"{i}. {question}\n"

    return {"has_questions": True, "questions": new_questions[:3], "message": question_text}


@tool
def get_plan_statistics(plan: dict[str, Any]) -> dict[str, Any]:
    """Get detailed statistics about a plan."""
    if not plan:
        return {"error": "No plan provided"}

    steps = plan.get("steps", [])
    history = plan.get("history", [])

    stats = {
        "title": plan.get("title", "Untitled"),
        "version": plan.get("version", 1),
        "total_steps": len(steps),
        "completed_steps": sum(1 for s in steps if s.get("status") == "completed"),
        "pending_steps": sum(1 for s in steps if s.get("status") == "pending"),
        "in_progress_steps": sum(1 for s in steps if s.get("status") == "in_progress"),
        "total_versions": len(history),
        "modification_count": len([h for h in history if h.get("action") == "updated"]),
        "completion_percentage": 0,
    }

    if stats["total_steps"] > 0:
        stats["completion_percentage"] = round(
            (stats["completed_steps"] / stats["total_steps"]) * 100, 1
        )

    return stats


@tool
def export_plan(plan: dict[str, Any], format: str = "markdown") -> str:
    """Export a plan to various formats."""
    if not plan:
        return "No plan to export"

    if format == "json":
        import json

        return json.dumps(plan, indent=2, default=str)

    elif format == "markdown":
        lines = [
            f"# {plan.get('title', 'Untitled Plan')}",
            "",
            f"**Version:** {plan.get('version', 1)}  ",
            f"**Created:** {plan.get('created_at', 'Unknown')}  ",
            f"**Updated:** {plan.get('updated_at', 'Unknown')}",
            "",
            "## Steps",
            "",
        ]

        for step in plan.get("steps", []):
            status = step.get("status", "pending")
            icon = "✅" if status == "completed" else "⬜"
            lines.append(f"{icon} **Step {step['id']}:** {step['description']}")

        lines.extend(["", "## Summary", "", plan.get("summary", "No summary available")])

        return "\n".join(lines)

    else:
        return generate_plan_summary.invoke({"plan": plan})


class PlanValidator:
    """Validates plans for logical consistency and completeness."""

    def validate(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Validate a plan and return issues and recommendations."""
        if not plan:
            return {"valid": False, "issues": ["No plan provided"], "recommendations": []}

        issues = []
        recommendations = []

        steps = plan.get("steps", [])
        metadata = plan.get("metadata", {})
        dependencies = metadata.get("dependencies", {})

        if not steps:
            issues.append("Plan has no steps")

        if len(steps) > 0:
            first_step = steps[0]
            if any(
                kw in first_step["description"].lower()
                for kw in ["test", "deploy", "launch", "release"]
            ):
                issues.append("First step appears to be an ending action - check step order")

        step_ids = {s["id"] for s in steps}
        for step_id, deps in dependencies.items():
            step_id_int = int(step_id) if isinstance(step_id, str) else step_id
            if step_id_int not in step_ids:
                issues.append(f"Dependency references non-existent step {step_id}")
            for dep in deps:
                if dep not in step_ids:
                    issues.append(f"Step {step_id} depends on non-existent step {dep}")

        descriptions = [s["description"].lower() for s in steps]
        for i, desc in enumerate(descriptions):
            for j, other_desc in enumerate(descriptions[i + 1 :], i + 1):
                if self._similarity(desc, other_desc) > 0.8:
                    recommendations.append(
                        f"Steps {i + 1} and {j + 1} appear similar - consider merging"
                    )

        milestone_ids = set(metadata.get("milestones", []))
        for ms_id in milestone_ids:
            if ms_id not in step_ids:
                issues.append(f"Milestone references non-existent step {ms_id}")

        if not metadata.get("estimated_duration") and len(steps) > 5:
            recommendations.append("Consider adding estimated duration to plan metadata")

        if len(steps) > 10 and not any(metadata.get("milestones", [])):
            recommendations.append("Large plan - consider adding milestones for better tracking")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "recommendations": recommendations,
        }

    def _similarity(self, a: str, b: str) -> float:
        """Calculate simple string similarity."""
        a_words = set(a.split())
        b_words = set(b.split())
        if not a_words or not b_words:
            return 0.0
        intersection = a_words & b_words
        union = a_words | b_words
        return len(intersection) / len(union)


class DependencyManager:
    """Manages step dependencies and critical path analysis."""

    def add_dependency(self, plan: dict[str, Any], step_id: int, depends_on: int) -> dict[str, Any]:
        """Add a dependency between steps."""
        plan = deepcopy(plan)
        metadata = plan.setdefault("metadata", {})
        dependencies = metadata.setdefault("dependencies", {})

        step_deps = dependencies.setdefault(str(step_id), [])
        if depends_on not in step_deps:
            step_deps.append(depends_on)

        return plan

    def remove_dependency(
        self, plan: dict[str, Any], step_id: int, depends_on: int
    ) -> dict[str, Any]:
        """Remove a dependency between steps."""
        plan = deepcopy(plan)
        metadata = plan.get("metadata", {})
        dependencies = metadata.get("dependencies", {})

        step_deps = dependencies.get(str(step_id), [])
        if depends_on in step_deps:
            step_deps.remove(depends_on)

        return plan

    def get_blocked_steps(self, plan: dict[str, Any]) -> list[int]:
        """Get steps that are blocked by incomplete dependencies."""
        metadata = plan.get("metadata", {})
        dependencies = metadata.get("dependencies", {})
        steps = plan.get("steps", [])

        completed_ids = {s["id"] for s in steps if s.get("status") == "completed"}
        blocked = []

        for step_id, deps in dependencies.items():
            step_id_int = int(step_id)
            if step_id_int not in completed_ids:
                incomplete_deps = [d for d in deps if d not in completed_ids]
                if incomplete_deps:
                    blocked.append(step_id_int)

        return blocked

    def get_ready_steps(self, plan: dict[str, Any]) -> list[int]:
        """Get steps that are ready to be worked on (all dependencies complete)."""
        metadata = plan.get("metadata", {})
        dependencies = metadata.get("dependencies", {})
        steps = plan.get("steps", [])

        completed_ids = {s["id"] for s in steps if s.get("status") == "completed"}
        ready = []

        for step in steps:
            if step.get("status") != "completed":
                deps = dependencies.get(str(step["id"]), [])
                if all(d in completed_ids for d in deps):
                    ready.append(step["id"])

        return ready


class DueDateManager:
    """Manages due dates and deadlines for plan steps."""

    def set_due_date(self, plan: dict[str, Any], step_id: int, due_date: str) -> dict[str, Any]:
        """Set a due date for a specific step."""
        plan = deepcopy(plan)
        steps = plan.get("steps", [])

        for step in steps:
            if step["id"] == step_id:
                step["due_date"] = due_date
                break

        return plan

    def get_overdue_steps(self, plan: dict[str, Any]) -> list[dict[str, Any]]:
        """Get steps that are past their due date."""
        steps = plan.get("steps", [])
        now = datetime.now()
        overdue = []

        for step in steps:
            if step.get("status") != "completed" and "due_date" in step:
                try:
                    due = datetime.fromisoformat(step["due_date"])
                    if due < now:
                        overdue.append(step)
                except ValueError:
                    continue

        return overdue

    def auto_schedule(
        self,
        plan: dict[str, Any],
        start_date: str | None = None,
        work_days: int = 5,
    ) -> dict[str, Any]:
        """Auto-assign due dates based on dependencies and estimates."""
        plan = deepcopy(plan)
        metadata = plan.get("metadata", {})
        dependencies = metadata.get("dependencies", {})
        steps = plan.get("steps", [])

        if not start_date:
            start_date = datetime.now().isoformat()

        current_date = datetime.fromisoformat(start_date)
        step_dates = {}

        for step in steps:
            step_id = step["id"]
            deps = dependencies.get(str(step_id), [])

            if deps:
                latest_dep_date = max(
                    (step_dates.get(d, current_date) for d in deps), default=current_date
                )
                current_date = latest_dep_date + timedelta(days=1)

            estimate = step.get("estimated_hours", 8)
            days_needed = max(1, estimate // (8 * work_days / 7))

            step["due_date"] = (current_date + timedelta(days=days_needed)).isoformat()
            step_dates[step_id] = current_date + timedelta(days=days_needed)
            current_date = step_dates[step_id] + timedelta(days=1)

        return plan


class BatchOperations:
    """Handles batch operations on plan steps."""

    def batch_update_status(
        self,
        plan: dict[str, Any],
        step_ids: list[int],
        status: str,
    ) -> dict[str, Any]:
        """Update status for multiple steps at once."""
        plan = deepcopy(plan)
        steps = plan.get("steps", [])
        timestamp = datetime.now().isoformat()

        for step in steps:
            if step["id"] in step_ids:
                step["status"] = status
                step["updated_at"] = timestamp

        return self._update_metadata(plan)

    def batch_add_steps(
        self,
        plan: dict[str, Any],
        descriptions: list[str],
    ) -> dict[str, Any]:
        """Add multiple steps at once."""
        plan = deepcopy(plan)
        steps = plan.get("steps", [])
        timestamp = datetime.now().isoformat()

        start_id = max((s["id"] for s in steps), default=0) + 1

        for i, desc in enumerate(descriptions):
            steps.append(
                {
                    "id": start_id + i,
                    "description": desc,
                    "status": "pending",
                    "created_at": timestamp,
                }
            )

        return self._update_metadata(plan)

    def batch_remove_steps(self, plan: dict[str, Any], step_ids: list[int]) -> dict[str, Any]:
        """Remove multiple steps at once."""
        plan = deepcopy(plan)
        steps = plan.get("steps", [])

        steps[:] = [s for s in steps if s["id"] not in step_ids]

        for i, step in enumerate(steps):
            step["id"] = i + 1

        return self._update_metadata(plan)

    def _update_metadata(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Update plan metadata after batch operations."""
        steps = plan.get("steps", [])
        completed = sum(1 for s in steps if s.get("status") == "completed")

        plan["metadata"] = {
            **plan.get("metadata", {}),
            "total_steps": len(steps),
            "completed_steps": completed,
            "status": "completed" if completed == len(steps) and steps else "in_progress",
        }

        return plan


class UndoRedoManager:
    """Manages undo/redo functionality for plans."""

    MAX_STACK_SIZE = 50

    def push_state(
        self,
        state: dict[str, Any],
        new_plan: dict[str, Any],
    ) -> dict[str, Any]:
        """Push current plan state onto undo stack before updating."""
        state = deepcopy(state)
        undo_stack = state.get("undo_stack", [])
        current_plan = state.get("current_plan", {})

        if current_plan:
            undo_stack.append(deepcopy(current_plan))
            if len(undo_stack) > self.MAX_STACK_SIZE:
                undo_stack.pop(0)

        state["undo_stack"] = undo_stack
        state["redo_stack"] = []
        state["current_plan"] = deepcopy(new_plan)
        return state

    def undo(self, state: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Undo the last plan change."""
        state = deepcopy(state)
        undo_stack = state.get("undo_stack", [])
        redo_stack = state.get("redo_stack", [])
        current_plan = state.get("current_plan", {})

        if not undo_stack:
            return None, state

        redo_stack.append(deepcopy(current_plan))
        previous_plan = undo_stack.pop()

        state["redo_stack"] = redo_stack
        state["undo_stack"] = undo_stack

        return previous_plan, state

    def redo(self, state: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Redo the last undone change."""
        state = deepcopy(state)
        redo_stack = state.get("redo_stack", [])
        undo_stack = state.get("undo_stack", [])
        current_plan = state.get("current_plan", {})

        if not redo_stack:
            return None, state

        undo_stack.append(deepcopy(current_plan))
        next_plan = redo_stack.pop()

        state["redo_stack"] = redo_stack
        state["undo_stack"] = undo_stack

        return next_plan, state

    def can_undo(self, state: dict[str, Any]) -> bool:
        """Check if undo is available."""
        return bool(state.get("undo_stack", []))

    def can_redo(self, state: dict[str, Any]) -> bool:
        """Check if redo is available."""
        return bool(state.get("redo_stack", []))


class RiskAssessor:
    """Assesses risks for plan steps."""

    RISK_KEYWORDS = {
        "high": ["critical", "urgent", "deadline", "external", "third-party", "approval", "legal"],
        "medium": ["integration", "testing", "review", "feedback", "coordination"],
    }

    def assess_risks(self, plan: dict[str, Any]) -> list[dict[str, Any]]:
        """Assess risks for each step in the plan."""
        steps = plan.get("steps", [])
        risks = []

        for step in steps:
            desc_lower = step["description"].lower()
            risk_level = "low"
            risk_factors = []

            for keyword in self.RISK_KEYWORDS["high"]:
                if keyword in desc_lower:
                    risk_level = "high"
                    risk_factors.append(f"Contains '{keyword}'")

            if risk_level == "low":
                for keyword in self.RISK_KEYWORDS["medium"]:
                    if keyword in desc_lower:
                        risk_level = "medium"
                        risk_factors.append(f"Contains '{keyword}'")

            dependencies = plan.get("metadata", {}).get("dependencies", {})
            deps = dependencies.get(str(step["id"]), [])
            if len(deps) > 2:
                risk_level = "high" if risk_level == "medium" else "medium"
                risk_factors.append(f"Has {len(deps)} dependencies")

            risks.append(
                {
                    "step_id": step["id"],
                    "description": step["description"],
                    "risk_level": risk_level,
                    "risk_factors": risk_factors,
                    "mitigation": self._suggest_mitigation(risk_level, risk_factors),
                }
            )

        return risks

    def _suggest_mitigation(self, risk_level: str, factors: list[str]) -> str:
        """Suggest mitigation strategies based on risk."""
        if risk_level == "low":
            return "Monitor as normal"
        elif "deadline" in str(factors).lower() or "urgent" in str(factors).lower():
            return "Add buffer time, set earlier internal deadline"
        elif "external" in str(factors).lower() or "third-party" in str(factors).lower():
            return "Establish clear SLAs, have backup options"
        elif "integration" in str(factors).lower():
            return "Plan integration testing early, document interfaces"
        else:
            return "Review regularly, identify blockers early"


class SmartEstimator:
    """Provides smart estimation for step duration."""

    COMPLEXITY_PATTERNS = {
        "simple": ["update", "fix", "review", "check", "verify", "send", "email"],
        "complex": ["develop", "build", "implement", "design", "architect", "integrate"],
        "research": ["research", "analyze", "investigate", "evaluate", "assess"],
    }

    def estimate_step(self, description: str) -> dict[str, Any]:
        """Estimate time and complexity for a step."""
        desc_lower = description.lower()

        step_type = "medium"
        for pattern in self.COMPLEXITY_PATTERNS["simple"]:
            if pattern in desc_lower:
                step_type = "simple"
                break

        for pattern in self.COMPLEXITY_PATTERNS["complex"]:
            if pattern in desc_lower:
                step_type = "complex"
                break

        for pattern in self.COMPLEXITY_PATTERNS["research"]:
            if pattern in desc_lower:
                step_type = "research"
                break

        estimates = {
            "simple": {"hours": 4, "days": 0.5, "confidence": "high"},
            "medium": {"hours": 8, "days": 1, "confidence": "medium"},
            "complex": {"hours": 24, "days": 3, "confidence": "medium"},
            "research": {"hours": 16, "days": 2, "confidence": "low"},
        }

        estimate = estimates[step_type]

        return {
            "description": description,
            "type": step_type,
            "estimated_hours": estimate["hours"],
            "estimated_days": estimate["days"],
            "confidence": estimate["confidence"],
        }

    def estimate_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Estimate total plan duration."""
        steps = plan.get("steps", [])

        total_hours = 0
        step_estimates = []

        for step in steps:
            estimate = self.estimate_step(step["description"])
            step_estimates.append(
                {
                    "step_id": step["id"],
                    **estimate,
                }
            )
            total_hours += estimate["estimated_hours"]

        working_days = total_hours / 8
        calendar_weeks = working_days / 5

        return {
            "total_hours": total_hours,
            "working_days": round(working_days, 1),
            "calendar_weeks": round(calendar_weeks, 1),
            "step_estimates": step_estimates,
            "confidence": "low"
            if calendar_weeks > 4
            else "medium"
            if calendar_weeks > 2
            else "high",
        }


class SuggestionEngine:
    """Generates smart suggestions for plans."""

    STEP_SUGGESTIONS = {
        "website": [
            "SEO optimization",
            "Performance testing",
            "Accessibility audit",
            "Mobile responsiveness",
        ],
        "app": [
            "App store optimization",
            "Crash analytics",
            "User onboarding",
            "Push notifications",
        ],
        "event": ["Contingency plan", "Weather backup", "Emergency contacts", "Post-event survey"],
        "trip": [
            "Travel insurance",
            "Local emergency numbers",
            "Backup accommodations",
            "Itinerary sharing",
        ],
        "project": ["Risk assessment", "Stakeholder updates", "Documentation", "Lessons learned"],
    }

    def suggest_missing_steps(self, plan: dict[str, Any]) -> list[str]:
        """Suggest steps that might be missing from the plan."""
        suggestions = []
        title_lower = plan.get("title", "").lower()
        steps = plan.get("steps", [])
        step_text = " ".join(s["description"].lower() for s in steps)

        for category, suggested_steps in self.STEP_SUGGESTIONS.items():
            if category in title_lower:
                for suggestion in suggested_steps:
                    if suggestion.lower() not in step_text:
                        suggestions.append(suggestion)

        has_testing = any("test" in s["description"].lower() for s in steps)
        has_review = any("review" in s["description"].lower() for s in steps)

        if len(steps) > 3 and not has_testing:
            suggestions.append("Testing/QA phase")

        if len(steps) > 5 and not has_review:
            suggestions.append("Review/feedback session")

        return suggestions[:5]

    def suggest_improvements(self, plan: dict[str, Any]) -> list[str]:
        """Suggest improvements to existing plan."""
        improvements = []
        steps = plan.get("steps", [])
        metadata = plan.get("metadata", {})

        if len(steps) > 10 and not metadata.get("milestones"):
            improvements.append("Add milestones to track progress on this large plan")

        deps = metadata.get("dependencies", {})
        if len(steps) > 5 and not deps:
            improvements.append("Consider adding dependencies between related steps")

        has_estimates = any("estimated_hours" in s for s in steps)
        if not has_estimates:
            improvements.append("Add time estimates to steps for better planning")

        return improvements


@tool
def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate a plan for logical consistency and completeness."""
    validator = PlanValidator()
    return validator.validate(plan)


@tool
def add_step_dependency(
    current_plan: dict[str, Any],
    step_id: int,
    depends_on: int,
) -> dict[str, Any]:
    """Add a dependency between two steps (step_id depends on depends_on)."""
    manager = DependencyManager()
    return manager.add_dependency(current_plan, step_id, depends_on)


@tool
def get_critical_path(current_plan: dict[str, Any]) -> dict[str, Any]:
    """Get steps that are ready to work on and blocked steps."""
    manager = DependencyManager()
    return {
        "ready_steps": manager.get_ready_steps(current_plan),
        "blocked_steps": manager.get_blocked_steps(current_plan),
    }


@tool
def set_step_due_date(
    current_plan: dict[str, Any],
    step_id: int,
    due_date: str,
) -> dict[str, Any]:
    """Set a due date for a specific step (ISO format: YYYY-MM-DD)."""
    manager = DueDateManager()
    return manager.set_due_date(current_plan, step_id, due_date)


@tool
def get_overdue_steps(current_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Get all steps that are past their due date."""
    manager = DueDateManager()
    return manager.get_overdue_steps(current_plan)


@tool
def auto_schedule_plan(
    current_plan: dict[str, Any],
    start_date: str | None = None,
) -> dict[str, Any]:
    """Automatically assign due dates to all steps based on dependencies."""
    manager = DueDateManager()
    return manager.auto_schedule(current_plan, start_date)


@tool
def batch_update_steps(
    current_plan: dict[str, Any],
    step_ids: list[int],
    status: str,
) -> dict[str, Any]:
    """Update status for multiple steps at once."""
    batch_ops = BatchOperations()
    return batch_ops.batch_update_status(current_plan, step_ids, status)


@tool
def assess_plan_risks(current_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Assess risks for all steps in the plan."""
    assessor = RiskAssessor()
    return assessor.assess_risks(current_plan)


@tool
def estimate_plan_duration(current_plan: dict[str, Any]) -> dict[str, Any]:
    """Estimate total plan duration with confidence levels."""
    estimator = SmartEstimator()
    return estimator.estimate_plan(current_plan)


@tool
def suggest_plan_improvements(current_plan: dict[str, Any]) -> dict[str, Any]:
    """Suggest missing steps and improvements for the plan."""
    engine = SuggestionEngine()
    return {
        "missing_steps": engine.suggest_missing_steps(current_plan),
        "improvements": engine.suggest_improvements(current_plan),
    }


@tool
def mark_milestone(
    current_plan: dict[str, Any],
    step_id: int,
) -> dict[str, Any]:
    """Mark a step as a key milestone."""
    plan = deepcopy(current_plan)
    metadata = plan.setdefault("metadata", {})
    milestones = metadata.setdefault("milestones", [])

    if step_id not in milestones:
        milestones.append(step_id)
        milestones.sort()

    for step in plan.get("steps", []):
        if step["id"] == step_id:
            step["is_milestone"] = True
            break

    return plan


@tool
def expand_step_with_substeps(
    current_plan: dict[str, Any],
    step_id: int,
    sub_steps: list[str],
) -> dict[str, Any]:
    """Expand a step into detailed sub-steps."""
    plan = deepcopy(current_plan)
    steps = plan.get("steps", [])
    timestamp = datetime.now().isoformat()

    for step in steps:
        if step["id"] == step_id:
            step["sub_steps"] = [
                {
                    "id": i + 1,
                    "description": sub_desc,
                    "status": "pending",
                    "created_at": timestamp,
                }
                for i, sub_desc in enumerate(sub_steps)
            ]
            break

    return plan


@tool
def fork_plan(
    current_plan: dict[str, Any],
    new_title: str,
) -> dict[str, Any]:
    """Create a copy of the current plan with a new title."""
    plan = deepcopy(current_plan)
    timestamp = datetime.now().isoformat()

    plan["title"] = new_title
    plan["version"] = 1
    plan["created_at"] = timestamp
    plan["updated_at"] = timestamp
    plan["history"] = [
        {
            "version": 1,
            "timestamp": timestamp,
            "action": "forked",
            "title": new_title,
            "steps": [s.copy() for s in plan.get("steps", [])],
        }
    ]
    plan["summary"] = f"Fork of plan: {new_title}"

    return plan
