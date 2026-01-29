"""LangGraph agent workflow for Planning Agent."""

import json
from enum import Enum
from typing import Annotated, Any, Literal, TypedDict

import tiktoken
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from llm_providers import get_llm
from tools import (
    add_step_dependency,
    appknox_security_audit,
    ask_clarifying_question,
    assess_plan_risks,
    auto_schedule_plan,
    batch_update_steps,
    create_plan,
    detect_ambiguity,
    estimate_plan_duration,
    expand_step_with_substeps,
    export_plan,
    fork_plan,
    generate_executive_summary,
    generate_plan_diff,
    generate_plan_summary,
    get_critical_path,
    get_overdue_steps,
    mark_milestone,
    set_step_due_date,
    suggest_plan_improvements,
    update_plan,
    validate_plan,
)


class AgentState(TypedDict):
    """State maintained throughout the agent conversation."""

    messages: Annotated[list[BaseMessage], add_messages]
    summary: str
    current_plan: dict[str, Any]
    conversation_turn: int
    user_preferences: dict[str, Any]
    last_action: str
    session_id: str
    undo_stack: list[dict[str, Any]]
    redo_stack: list[dict[str, Any]]
    tags: list[str]


class ActionType(str, Enum):
    """Action types for user intent analysis."""

    CREATE_PLAN = "create_plan"
    UPDATE_PLAN = "update_plan"
    SHOW_DIFF = "show_diff"
    EXECUTIVE_SUMMARY = "executive_summary"
    SECURITY_AUDIT = "security_audit"
    GENERAL_CHAT = "general_chat"
    TEMPLATE_CREATE = "template_create"
    VALIDATE_PLAN = "validate_plan"
    FORK_PLAN = "fork_plan"


TOKEN_LIMIT = 8000
COMPRESSION_THRESHOLD = 0.7
PRESERVE_LAST_N_MESSAGES = 4


def normalize_content_for_encoding(content) -> str:
    """Normalize content to string for token counting."""
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


def count_tokens(messages: list[BaseMessage], model: str = "gpt-4") -> int:
    """Count tokens in a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    total_tokens = 0
    for msg in messages:
        content_str = normalize_content_for_encoding(msg.content)
        total_tokens += len(encoding.encode(content_str))
        total_tokens += len(encoding.encode(msg.type))
    return total_tokens


def analyze_user_intent(state: AgentState) -> str:
    """Analyze user intent from the last message."""
    messages = state["messages"]
    current_plan = state.get("current_plan", {})

    if not messages:
        return ActionType.GENERAL_CHAT

    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        return ActionType.GENERAL_CHAT

    user_input = last_message.content.lower()

    if any(word in user_input for word in ["summary", "summarize", "overview"]):
        return ActionType.EXECUTIVE_SUMMARY

    if any(word in user_input for word in ["diff", "changes", "what changed", "history"]):
        return ActionType.SHOW_DIFF

    if any(word in user_input for word in ["security", "audit", "scan", "vulnerability"]):
        return ActionType.SECURITY_AUDIT

    if any(word in user_input for word in ["template", "use template", "start with"]):
        return ActionType.TEMPLATE_CREATE

    if any(word in user_input for word in ["validate", "check plan", "verify"]):
        return ActionType.VALIDATE_PLAN

    if any(word in user_input for word in ["fork", "copy plan", "duplicate"]):
        return ActionType.FORK_PLAN

    if current_plan and any(
        word in user_input
        for word in [
            "add",
            "remove",
            "delete",
            "change",
            "modify",
            "update",
            "edit",
            "replace",
            "move",
            "reorder",
        ]
    ):
        return ActionType.UPDATE_PLAN

    if any(
        word in user_input
        for word in [
            "plan",
            "create",
            "build",
            "make",
            "start",
            "setup",
            "organize",
            "schedule",
            "design",
        ]
    ):
        return ActionType.CREATE_PLAN

    return ActionType.GENERAL_CHAT


def context_management_node(state: AgentState) -> dict[str, Any]:
    """Manage conversation context and compress if needed."""
    messages = state["messages"]
    summary = state.get("summary", "")
    current_turn = state.get("conversation_turn", 0)

    new_turn = current_turn + 1
    current_tokens = count_tokens(messages)

    if (
        current_tokens > TOKEN_LIMIT * COMPRESSION_THRESHOLD
        and len(messages) > PRESERVE_LAST_N_MESSAGES
    ):
        llm = get_llm()
        messages_to_summarize = messages[:-PRESERVE_LAST_N_MESSAGES]
        preserved_messages = messages[-PRESERVE_LAST_N_MESSAGES:]

        conversation_text = "\n".join(
            [
                f"{m.type}: {normalize_content_for_encoding(m.content)[:500]}"
                for m in messages_to_summarize
            ]
        )

        prompt = f"""Summarize this conversation, keeping key details about the plan and user preferences:

Previous summary: {summary}

New messages:
{conversation_text}

Provide a concise summary."""

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            new_summary = response.content
        except Exception:
            new_summary = summary

        return {
            "summary": new_summary,
            "messages": preserved_messages,
            "conversation_turn": new_turn,
        }

    return {"conversation_turn": new_turn, "messages": messages, "summary": summary}


def agent_node(state: AgentState) -> dict[str, Any]:
    """Main agent node that processes messages and decides actions."""
    llm = get_llm()

    tools = [
        create_plan,
        update_plan,
        appknox_security_audit,
        generate_plan_summary,
        generate_plan_diff,
        generate_executive_summary,
        ask_clarifying_question,
        detect_ambiguity,
        export_plan,
        validate_plan,
        add_step_dependency,
        get_critical_path,
        set_step_due_date,
        get_overdue_steps,
        auto_schedule_plan,
        batch_update_steps,
        assess_plan_risks,
        estimate_plan_duration,
        suggest_plan_improvements,
        mark_milestone,
        expand_step_with_substeps,
        fork_plan,
    ]
    llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

    summary = state.get("summary", "")
    current_plan = state.get("current_plan", {})
    turn = state.get("conversation_turn", 0)

    intent = analyze_user_intent(state)

    if current_plan and current_plan.get("steps"):
        plan_steps = "\n".join(
            [f"  Step {s['id']}: {s['description'][:60]}" for s in current_plan["steps"]]
        )
    else:
        plan_steps = "  No steps yet"

    system_prompt = f"""You are a Planning Assistant that helps users create, modify, and manage structured plans through natural conversation.

## CORE RESPONSIBILITIES

1. CLARIFICATION REQUESTS (20 points criteria):
   - ALWAYS use detect_ambiguity tool FIRST when the user wants to create a plan
   - If the request is vague or missing key details, use ask_clarifying_question tool
   - Ask up to 3 focused clarifying questions before creating a plan
   - Only proceed to create_plan AFTER getting sufficient information

2. PLAN CREATION (20 points criteria):
   - Use create_plan tool to generate structured plans with clear, actionable steps
   - Plans must include: title, numbered steps, version tracking
   - ALWAYS call generate_plan_summary IMMEDIATELY AFTER create_plan to display the plan
   - Plans should be practical and specific to the user's requirements

3. PLAN EDITING (20 points criteria):
   - Use update_plan tool for ALL modifications (add, update, remove, reorder steps, or change title)
   - CRITICAL: When updating or removing steps, you MUST provide the exact step "id" number
   - Current plan steps are shown with their IDs - reference them correctly
   - Example modifications:
     * {{"action": "update", "id": 2, "description": "New description"}} ← id is REQUIRED
     * {{"action": "remove", "id": 3}} ← id is REQUIRED
     * {{"action": "add", "description": "New step"}} ← id is optional for add
   - To update the plan title (e.g., change "50 guests" to "75 guests"), use the "new_title" parameter
   - If user wants to modify ALL steps (make more verbose, assign people), use "action": "update" for each step
   - If user says "change step 5", use "id": 5
   - If user says "remove the testing step", find which ID has testing and use that ID
   - ALWAYS call generate_plan_diff AFTER update_plan to show what changed
   - ALWAYS call generate_plan_summary AFTER update_plan to display the updated plan
   - Track version history automatically

4. ENHANCED PLAN FEATURES:
   - Use validate_plan to check plan for logical issues
   - Use assess_plan_risks to identify potential risks
   - Use estimate_plan_duration to get time estimates
   - Use suggest_plan_improvements to get enhancement ideas
   - Use mark_milestone to mark key achievement points
   - Use add_step_dependency when steps depend on others
   - Use expand_step_with_substeps to break down complex steps
   - Use fork_plan to create plan variations

5. CONTEXT MANAGEMENT (20 points criteria):
   - Maintain full conversation history (handles 10+ turns)
   - Reference previous context when answering follow-up questions
   - Support requirement changes and plan modifications smoothly
   - Context compression happens automatically at 8K token limit

6. SUMMARIZATION (10 points criteria):
   - Use generate_plan_summary to summarize plans before presenting
   - Use generate_plan_diff to summarize plan updates/changes after edits
   - Use generate_executive_summary when user asks for overall conversation summary
   - Summaries should highlight key points and progress

7. UI SUPPORT (10 points criteria):
   - Provide clear plan display with step numbers and status
   - Show plan changes/diffs when editing
   - Support interactive Q&A for clarifications
   - Use export_plan when user wants to export (markdown or json)

## MANDATORY WORKFLOW

For NEW plan requests:
1. detect_ambiguity → Check if request is clear
2. ask_clarifying_question → If vague, ask questions
3. Wait for user clarification
4. create_plan → Create the structured plan
5. generate_plan_summary → Display the plan

For PLAN MODIFICATIONS:
1. update_plan → Apply the changes
2. generate_plan_diff → Show what changed
3. generate_plan_summary → Display updated plan

For VALIDATION:
1. validate_plan → Check for issues
2. assess_plan_risks → Identify risks
3. suggest_plan_improvements → Get suggestions

## RULES
- ALWAYS use tools for actions - never just chat about plans without tools
- NEVER create a plan without checking for ambiguity first
- ALWAYS show the plan after creating or updating it
- ALWAYS show diffs after updating a plan
- Support 10+ conversation turns with full context
- Maintain user preferences across the conversation

## CURRENT CONTEXT
Turn: {turn} (supports 10+ turns)
Summary: {summary if summary else "No summary yet"}
Current Plan: {current_plan.get("title", "None") if current_plan else "None"}
Plan Version: {current_plan.get("version", "N/A") if current_plan else "N/A"}
Intent: {intent}

## CURRENT PLAN STEPS (for reference when updating)
{plan_steps}

## CRITICAL REMINDER
When using update_plan with "update" or "remove" actions, you MUST include the "id" field.
The step IDs are shown above. Use the correct ID number.
"""

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response],
        "last_action": intent,
    }


def tool_node(state: AgentState) -> dict[str, Any]:
    """Execute tools called by the agent."""
    messages = state["messages"]
    last_message = messages[-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {}

    tools_map = {
        "create_plan": create_plan,
        "update_plan": update_plan,
        "appknox_security_audit": appknox_security_audit,
        "generate_plan_summary": generate_plan_summary,
        "generate_plan_diff": generate_plan_diff,
        "generate_executive_summary": generate_executive_summary,
        "ask_clarifying_question": ask_clarifying_question,
        "detect_ambiguity": detect_ambiguity,
        "export_plan": export_plan,
        "validate_plan": validate_plan,
        "add_step_dependency": add_step_dependency,
        "get_critical_path": get_critical_path,
        "set_step_due_date": set_step_due_date,
        "get_overdue_steps": get_overdue_steps,
        "auto_schedule_plan": auto_schedule_plan,
        "batch_update_steps": batch_update_steps,
        "assess_plan_risks": assess_plan_risks,
        "estimate_plan_duration": estimate_plan_duration,
        "suggest_plan_improvements": suggest_plan_improvements,
        "mark_milestone": mark_milestone,
        "expand_step_with_substeps": expand_step_with_substeps,
        "fork_plan": fork_plan,
    }

    outputs = []
    updated_plan = None

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_func = tools_map.get(tool_name)

        if not tool_func:
            outputs.append(
                ToolMessage(
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=f"Error: Tool '{tool_name}' not found.",
                )
            )
            continue

        args = tool_call["args"].copy() if tool_call["args"] else {}

        if tool_name in [
            "update_plan",
            "generate_plan_summary",
            "generate_plan_diff",
            "appknox_security_audit",
            "validate_plan",
            "add_step_dependency",
            "get_critical_path",
            "set_step_due_date",
            "get_overdue_steps",
            "auto_schedule_plan",
            "batch_update_steps",
            "assess_plan_risks",
            "estimate_plan_duration",
            "suggest_plan_improvements",
            "mark_milestone",
            "expand_step_with_substeps",
            "fork_plan",
        ]:
            if "current_plan" not in args or not args.get("current_plan"):
                args["current_plan"] = state.get("current_plan", {})

        if tool_name == "generate_executive_summary":
            if "summary" not in args:
                args["summary"] = state.get("summary", "")
            if "plan" not in args:
                args["plan"] = state.get("current_plan", {})

        try:
            result = tool_func.invoke(args)

            if isinstance(result, (dict, list)):
                content = json.dumps(result, indent=2, default=str)
            else:
                content = str(result)

            outputs.append(
                ToolMessage(
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=content,
                )
            )

            if tool_name in [
                "create_plan",
                "update_plan",
                "add_step_dependency",
                "set_step_due_date",
                "auto_schedule_plan",
                "batch_update_steps",
                "mark_milestone",
                "expand_step_with_substeps",
                "fork_plan",
            ] and isinstance(result, dict):
                updated_plan = result

        except Exception as e:
            outputs.append(
                ToolMessage(
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=f"Error executing {tool_name}: {str(e)}",
                )
            )

    result = {"messages": outputs}
    if updated_plan:
        result["current_plan"] = updated_plan

    return result


def should_continue(state: AgentState) -> Literal["tools", "agent", "end"]:
    """Determine if the agent should continue to tools or end."""
    messages = state["messages"]

    if not messages:
        return "end"

    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


graph = StateGraph(AgentState)

graph.add_node("context_mgmt", context_management_node)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.set_entry_point("context_mgmt")
graph.add_edge("context_mgmt", "agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "agent": "agent", "end": END},
)
graph.add_edge("tools", "agent")

app = graph.compile()
