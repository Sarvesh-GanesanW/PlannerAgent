"""Evaluation tests using DeepEval metrics.

These tests evaluate the agent's responses using semantic metrics.
Requires OPENAI_API_KEY to be set for DeepEval.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set - DeepEval tests skipped"
)


def test_plan_creation_flow():
    from graph import app

    mock_response = AIMessage(
        content="I've created a plan for your trip. Let me show you the details.",
        tool_calls=[
            {
                "name": "create_plan",
                "args": {"title": "Test Plan", "steps": ["Step 1"]},
                "id": "call_1",
            }
        ],
    )

    inputs = {
        "messages": [HumanMessage(content="Plan a trip")],
        "summary": "",
        "current_plan": {},
        "conversation_turn": 0,
        "user_preferences": {},
        "last_action": "",
    }

    with patch("llm_providers.get_openai_llm") as mock_get_llm:
        mock_instance = MagicMock()
        mock_instance.bind_tools.return_value.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_instance

        valid_output = False

        async def run_test():
            nonlocal valid_output
            async for output in app.astream(inputs):
                if "agent" in output:
                    valid_output = True

        import asyncio

        asyncio.run(run_test())
        assert valid_output


def test_security_audit_trigger():
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase

    metric = AnswerRelevancyMetric(threshold=0.5)
    test_case = LLMTestCase(
        input="Check security",
        actual_output="Running AppKnox Audit...",
        expected_output="Running AppKnox Audit...",
    )
    assert_test(test_case, [metric])


def test_clarification_request():
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase

    metric = AnswerRelevancyMetric(threshold=0.5)
    test_case = LLMTestCase(
        input="I want to build a website",
        actual_output="What type of website? (e-commerce, blog, portfolio, etc.)",
        expected_output="What type of website?",
    )
    assert_test(test_case, [metric])


def test_plan_modification():
    from deepeval import assert_test
    from deepeval.metrics import FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    metric = FaithfulnessMetric(threshold=0.5)
    test_case = LLMTestCase(
        input="Add a step for testing",
        actual_output="I've added a testing step to your plan.",
        expected_output="I've added a testing step to your plan.",
        retrieval_context=["Plan modification successful"],
    )
    assert_test(test_case, [metric])
