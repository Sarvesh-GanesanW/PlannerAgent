import pytest
from langchain_core.messages import AIMessage, HumanMessage

from graph import ActionType, AgentState, analyze_user_intent, count_tokens
from tools import (
    appknox_security_audit,
    ask_clarifying_question,
    create_plan,
    detect_ambiguity,
    export_plan,
    generate_executive_summary,
    generate_plan_diff,
    generate_plan_summary,
    get_plan_statistics,
    update_plan,
)


def test_create_plan_basic():
    result = create_plan.invoke({"title": "Test Plan", "steps": ["Step 1", "Step 2"]})
    plan = result
    assert plan["title"] == "Test Plan"
    assert plan["version"] == 1
    assert len(plan["steps"]) == 2
    assert plan["steps"][0]["description"] == "Step 1"
    assert plan["steps"][1]["description"] == "Step 2"
    assert "history" in plan
    assert len(plan["history"]) == 1
    assert "summary" in plan


def test_create_plan_with_summary():
    result = create_plan.invoke({"title": "Trip to Paris", "steps": ["Book flight", "Book hotel"]})
    plan = result
    assert "summary" in plan
    assert "Trip to Paris" in plan["summary"]
    assert "2 steps" in plan["summary"]


def test_create_plan_empty_steps():
    result = create_plan.invoke({"title": "Empty Plan", "steps": []})
    plan = result
    assert plan["metadata"]["total_steps"] == 0


def test_update_plan_add_step():
    initial_result = create_plan.invoke({"title": "Test Plan", "steps": ["Step 1"]})
    initial_plan = initial_result
    assert initial_plan["version"] == 1
    assert len(initial_plan["steps"]) == 1

    modifications = [{"action": "add", "description": "Step 2"}]
    updated_result = update_plan.invoke(
        {"current_plan": initial_plan, "modifications": modifications}
    )
    updated = updated_result

    assert updated["version"] == 2
    assert len(updated["steps"]) == 2
    assert updated["steps"][1]["description"] == "Step 2"
    assert len(updated["history"]) == 2


def test_update_plan_modify_step():
    initial_result = create_plan.invoke({"title": "Test Plan", "steps": ["Original step"]})
    initial_plan = initial_result
    modifications = [{"action": "update", "id": 1, "description": "Modified step"}]
    updated_result = update_plan.invoke(
        {"current_plan": initial_plan, "modifications": modifications}
    )
    updated = updated_result

    assert updated["version"] == 2
    assert updated["steps"][0]["description"] == "Modified step"
    assert "Modified step" in updated["summary"]


def test_update_plan_remove_step():
    initial_result = create_plan.invoke(
        {"title": "Test Plan", "steps": ["Step 1", "Step 2", "Step 3"]}
    )
    initial_plan = initial_result

    modifications = [{"action": "remove", "id": 2}]
    updated_result = update_plan.invoke(
        {"current_plan": initial_plan, "modifications": modifications}
    )
    updated = updated_result

    assert updated["version"] == 2
    assert len(updated["steps"]) == 2
    assert updated["steps"][0]["id"] == 1
    assert updated["steps"][1]["id"] == 2


def test_update_plan_status():
    result = create_plan.invoke({"title": "Test Plan", "steps": ["Step 1"]})
    plan = result
    modifications = [{"action": "update", "id": 1, "status": "completed"}]
    updated_result = update_plan.invoke({"current_plan": plan, "modifications": modifications})
    updated = updated_result

    assert updated["steps"][0]["status"] == "completed"
    assert updated["version"] == 2


def test_update_plan_multiple_modifications():
    initial_result = create_plan.invoke({"title": "Test Plan", "steps": ["Step 1"]})
    initial_plan = initial_result

    modifications = [
        {"action": "update", "id": 1, "description": "Updated Step 1"},
        {"action": "add", "description": "Step 2"},
        {"action": "add", "description": "Step 3"},
    ]
    updated_result = update_plan.invoke(
        {"current_plan": initial_plan, "modifications": modifications}
    )
    updated = updated_result

    assert updated["version"] == 2
    assert len(updated["steps"]) == 3
    assert updated["steps"][0]["description"] == "Updated Step 1"


def test_plan_history_tracking():
    result = create_plan.invoke({"title": "History Test", "steps": ["Step 1"]})
    plan = result
    assert len(plan["history"]) == 1
    assert plan["history"][0]["version"] == 1

    updated_result = update_plan.invoke(
        {"current_plan": plan, "modifications": [{"action": "add", "description": "Step 2"}]}
    )
    updated = updated_result
    assert len(updated["history"]) == 2
    assert updated["history"][1]["version"] == 2
    assert "changes" in updated["history"][1]


def test_plan_history_preserves_old_versions():
    initial = create_plan.invoke({"title": "Test", "steps": ["Original"]})

    v2 = update_plan.invoke(
        {
            "current_plan": initial,
            "modifications": [{"action": "update", "id": 1, "description": "Version 2"}],
        }
    )

    v3 = update_plan.invoke(
        {
            "current_plan": v2,
            "modifications": [{"action": "update", "id": 1, "description": "Version 3"}],
        }
    )

    assert len(v3["history"]) == 3
    assert v3["history"][0]["steps"][0]["description"] == "Original"
    assert v3["history"][1]["steps"][0]["description"] == "Version 2"


def test_generate_plan_summary():
    result = create_plan.invoke({"title": "Test Plan", "steps": ["Step 1", "Step 2", "Step 3"]})
    plan = result
    summary = generate_plan_summary.invoke({"plan": plan})

    assert "Test Plan" in summary
    assert "3" in summary or "three" in summary.lower()


def test_generate_plan_summary_empty():
    summary = generate_plan_summary.invoke({"plan": {}})
    assert "No plan" in summary or "no plan" in summary.lower()


def test_generate_plan_diff():
    result = create_plan.invoke({"title": "Test Plan", "steps": ["Step 1"]})
    plan = result
    updated_result = update_plan.invoke(
        {"current_plan": plan, "modifications": [{"action": "add", "description": "Step 2"}]}
    )
    updated = updated_result
    diff = generate_plan_diff.invoke({"plan": updated})

    assert "Step 2" in diff
    assert "ADDED" in diff or "added" in diff.lower()


def test_generate_plan_diff_no_history():
    plan = {"title": "Test", "steps": []}
    diff = generate_plan_diff.invoke({"plan": plan})
    assert "No previous" in diff or "no" in diff.lower()


def test_generate_plan_diff_modification():
    result = create_plan.invoke({"title": "Test Plan", "steps": ["Original"]})
    plan = result
    updated_result = update_plan.invoke(
        {
            "current_plan": plan,
            "modifications": [{"action": "update", "id": 1, "description": "Modified"}],
        }
    )
    updated = updated_result
    diff = generate_plan_diff.invoke({"plan": updated})

    assert "Modified" in diff or "modified" in diff.lower()
    assert "Original" in diff


def test_generate_executive_summary():
    result = create_plan.invoke({"title": "Test Plan", "steps": ["Step 1", "Step 2"]})
    plan = result
    summary_text = "Discussed requirements for the test plan."
    exec_summary = generate_executive_summary.invoke({"summary": summary_text, "plan": plan})

    assert "Test Plan" in exec_summary or "EXECUTIVE" in exec_summary


def test_generate_executive_summary_empty():
    exec_summary = generate_executive_summary.invoke({"summary": "", "plan": {}})
    assert "No plan" in exec_summary or "No conversation" in exec_summary


def test_appknox_security_audit():
    plan = {"steps": [{"id": 1, "description": "Code step"}]}
    result = appknox_security_audit.invoke({"plan": plan})

    assert "SAST" in result
    assert "DAST" in result
    assert "Security" in result or "security" in result.lower()


def test_token_counting():
    messages = [
        HumanMessage(content="Hello world, this is a test message."),
        AIMessage(content="This is the response."),
    ]
    token_count = count_tokens(messages)
    assert token_count > 0
    assert token_count > 10


def test_token_counting_empty():
    messages = []
    token_count = count_tokens(messages)
    assert token_count == 0


def test_token_counting_large_messages():
    large_content = "Word " * 1000
    messages = [HumanMessage(content=large_content)]
    token_count = count_tokens(messages)
    assert token_count > 500


def test_detect_ambiguity_vague_request():
    result = detect_ambiguity.invoke({"user_input": "I want to build something"})
    assert result["is_ambiguous"] is True
    assert len(result["questions"]) > 0


def test_detect_ambiguity_clear_request():
    result = detect_ambiguity.invoke(
        {
            "user_input": "I want to build an e-commerce website selling books with a 3 month timeline"
        }
    )
    assert isinstance(result["is_ambiguous"], bool)


def test_detect_ambiguity_website():
    result = detect_ambiguity.invoke({"user_input": "I want to build a website"})
    assert result["is_ambiguous"] is True
    assert any("type" in q.lower() for q in result["questions"])


def test_detect_ambiguity_trip():
    result = detect_ambiguity.invoke({"user_input": "Plan a trip"})
    assert result["is_ambiguous"] is True
    assert any("where" in q.lower() or "destination" in q.lower() for q in result["questions"])


def test_detect_ambiguity_event():
    result = detect_ambiguity.invoke({"user_input": "I want to plan an event"})
    assert result["is_ambiguous"] is True


def test_ask_clarifying_question():
    result = ask_clarifying_question.invoke(
        {
            "context": "User wants to build a website",
            "missing_info": ["What type of website?", "What's the timeline?"],
        }
    )
    assert result["has_questions"] is True
    assert len(result["questions"]) == 2


def test_ask_clarifying_question_no_duplicates():
    result = ask_clarifying_question.invoke(
        {
            "context": "User wants to build a website",
            "missing_info": ["What type?", "What's the timeline?"],
            "previous_questions": ["What type?"],
        }
    )
    assert "What type?" not in result.get("questions", [])


def test_get_plan_statistics():
    plan = create_plan.invoke({"title": "Stats Test", "steps": ["Step 1", "Step 2", "Step 3"]})
    plan = update_plan.invoke(
        {
            "current_plan": plan,
            "modifications": [{"action": "update", "id": 1, "status": "completed"}],
        }
    )

    stats = get_plan_statistics.invoke({"plan": plan})

    assert stats["total_steps"] == 3
    assert stats["completed_steps"] == 1
    assert stats["pending_steps"] == 2
    assert stats["completion_percentage"] == 33.3 or stats["completion_percentage"] == 100 / 3


def test_export_plan_markdown():
    plan = create_plan.invoke({"title": "Export Test", "steps": ["Step 1", "Step 2"]})
    export = export_plan.invoke({"plan": plan, "format": "markdown"})

    assert "# Export Test" in export
    assert "Step 1" in export
    assert "Step 2" in export


def test_export_plan_json():
    plan = create_plan.invoke({"title": "JSON Test", "steps": ["Step 1"]})
    export = export_plan.invoke({"plan": plan, "format": "json"})

    import json

    data = json.loads(export)
    assert data["title"] == "JSON Test"
    assert len(data["steps"]) == 1


def test_analyze_intent_create_plan():
    state: AgentState = {
        "messages": [HumanMessage(content="I want to plan a trip to Paris")],
        "summary": "",
        "current_plan": {},
        "conversation_turn": 1,
        "user_preferences": {},
        "last_action": "",
    }
    result = analyze_user_intent(state)
    assert result in [ActionType.CREATE_PLAN, ActionType.GENERAL_CHAT]


def test_analyze_intent_modify_plan():
    state: AgentState = {
        "messages": [HumanMessage(content="Add a step for booking flights")],
        "summary": "",
        "current_plan": {"title": "Trip", "steps": [{"id": 1, "description": "Step 1"}]},
        "conversation_turn": 3,
        "user_preferences": {},
        "last_action": "",
    }
    result = analyze_user_intent(state)
    assert result in [ActionType.UPDATE_PLAN, ActionType.GENERAL_CHAT]


def test_full_plan_workflow():
    plan = create_plan.invoke(
        {
            "title": "Website Project",
            "steps": ["Design mockups", "Develop frontend", "Develop backend"],
        }
    )

    plan = update_plan.invoke(
        {
            "current_plan": plan,
            "modifications": [
                {"action": "add", "description": "Testing"},
                {"action": "add", "description": "Deployment"},
            ],
        }
    )

    plan = update_plan.invoke(
        {
            "current_plan": plan,
            "modifications": [
                {"action": "update", "id": 1, "status": "completed"},
                {"action": "update", "id": 2, "status": "completed"},
            ],
        }
    )

    assert plan["version"] == 3
    assert len(plan["steps"]) == 5
    assert plan["steps"][0]["status"] == "completed"
    assert plan["steps"][2]["status"] == "pending"
    assert plan["metadata"]["completed_steps"] == 2


def test_multi_turn_conversation_simulation():
    conversation_history = []

    conversation_history.append(HumanMessage(content="I want to build a mobile app"))
    conversation_history.append(AIMessage(content="What type of app?"))
    conversation_history.append(HumanMessage(content="An e-commerce app for selling clothes"))

    plan = create_plan.invoke(
        {
            "title": "E-commerce Clothing App",
            "steps": [
                "Design UI/UX",
                "Set up database",
                "Implement auth",
                "Build product catalog",
                "Add shopping cart",
                "Integrate payments",
            ],
        }
    )

    conversation_history.append(HumanMessage(content="Add a step for push notifications"))
    plan = update_plan.invoke(
        {
            "current_plan": plan,
            "modifications": [{"action": "add", "description": "Implement push notifications"}],
        }
    )

    assert len(conversation_history) >= 4
    assert plan["version"] == 2
    assert len(plan["steps"]) == 7
    assert any("push" in s["description"].lower() for s in plan["steps"])


def test_context_management_no_compression():
    """Test that context_management_node returns correct state when no compression needed."""
    from graph import context_management_node

    state = {
        "messages": [HumanMessage(content="Hello")],
        "summary": "",
        "current_plan": {},
        "conversation_turn": 0,
        "user_preferences": {},
        "last_action": "",
    }

    result = context_management_node(state)

    assert result["conversation_turn"] == 1
    assert "messages" in result
    assert "summary" in result
    assert len(result["messages"]) == 1


def test_context_management_turn_increment():
    """Test that conversation_turn is properly incremented."""
    from graph import context_management_node

    state = {
        "messages": [],
        "summary": "Existing summary",
        "current_plan": {},
        "conversation_turn": 5,
        "user_preferences": {},
        "last_action": "",
    }

    result = context_management_node(state)

    assert result["conversation_turn"] == 6
    assert result["summary"] == "Existing summary"


def test_export_plan_integration():
    """Test that export_plan tool is properly integrated."""
    from tools import export_plan

    plan = create_plan.invoke({"title": "Integration Test", "steps": ["Step 1", "Step 2"]})

    # Test markdown export
    markdown = export_plan.invoke({"plan": plan, "format": "markdown"})
    assert "# Integration Test" in markdown
    assert "Step 1" in markdown

    # Test JSON export
    json_output = export_plan.invoke({"plan": plan, "format": "json"})
    assert "Integration Test" in json_output


def test_context_management_preserves_summary():
    """Test that context_management_node preserves existing summary."""
    from graph import context_management_node

    existing_summary = "Previous conversation about trip planning"
    state = {
        "messages": [HumanMessage(content="New message")],
        "summary": existing_summary,
        "current_plan": {"title": "Trip"},
        "conversation_turn": 3,
        "user_preferences": {},
        "last_action": "",
    }

    result = context_management_node(state)

    # When no compression happens, summary should be preserved
    assert result["summary"] == existing_summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
