"""LLM provider abstractions for Planning Agent.

Provides unified interface for different LLM backends (Bedrock, Anthropic).
Handles credential management, model selection, and client initialization.
"""

import os
from enum import Enum

from langchain_core.language_models.chat_models import BaseChatModel


class Provider(str, Enum):
    """Supported LLM providers."""
    BEDROCK = "bedrock"
    ANTHROPIC = "anthropic"


RECOMMENDED_MODELS = {
    Provider.BEDROCK: [
        "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "global.anthropic.claude-opus-4-5-20251101-v1:0",
    ],
    Provider.ANTHROPIC: ["claude-sonnet-4-5-20250929", "claude-opus-4-5-20251101"],
}


def get_bedrock_llm(model_id: str, temperature: float, region_name: str | None = None):
    """Initialize Bedrock LLM client.
    
    Args:
        model_id: Bedrock model identifier
        temperature: Sampling temperature
        region_name: AWS region (defaults to us-east-1)
        
    Returns:
        Configured ChatBedrock instance
    """
    from langchain_aws import ChatBedrock

    if "opus" in model_id.lower():
        max_tokens = 32768
    else:
        max_tokens = 64000

    return ChatBedrock(
        model_id=model_id,
        temperature=temperature,
        region_name=region_name or os.environ.get("AWS_REGION", "us-east-1"),
        max_tokens=max_tokens,
    )


def get_anthropic_llm(model: str, temperature: float, api_key: str | None):
    """Initialize Anthropic LLM client.
    
    Args:
        model: Anthropic model name
        temperature: Sampling temperature
        api_key: API key (defaults to ANTHROPIC_API_KEY env var)
        
    Returns:
        Configured ChatAnthropic instance
    """
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model_name=model,
        temperature=temperature,
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
    )


def has_bedrock_credentials() -> bool:
    """Check if Bedrock credentials are available (API key or AWS credentials)."""
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return True
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return True
    return False


def get_llm(temperature: float = 0.1) -> BaseChatModel:
    """Get configured LLM instance based on environment settings.
    
    Automatically detects provider from environment variables if not specified.
    Raises ValueError if no credentials are found.
    
    Args:
        temperature: Sampling temperature for generation
        
    Returns:
        Configured LLM instance (ChatBedrock or ChatAnthropic)
        
    Raises:
        ValueError: If no valid credentials are found for any provider
    """
    provider_str = os.environ.get("LLM_PROVIDER", "auto").lower()

    if provider_str == "auto":
        if has_bedrock_credentials():
            provider_str = "bedrock"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            provider_str = "anthropic"
        else:
            raise ValueError(
                "No credentials found. Set AWS_BEARER_TOKEN_BEDROCK for Bedrock API key, "
                "or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY for AWS credentials, "
                "or ANTHROPIC_API_KEY for Anthropic"
            )

    provider = Provider(provider_str)

    if provider == Provider.BEDROCK:
        model_id = os.environ.get(
            "BEDROCK_MODEL", "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        region = os.environ.get("AWS_REGION", "us-east-1")
        return get_bedrock_llm(model_id, temperature, region)

    elif provider == Provider.ANTHROPIC:
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        return get_anthropic_llm(model, temperature, None)

    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_current_provider_info() -> dict:
    """Get information about the current LLM provider.
    
    Returns:
        Dict with provider name, model, and availability status
    """
    provider = os.environ.get("LLM_PROVIDER", "auto")

    if provider == "auto":
        if has_bedrock_credentials():
            provider = "bedrock"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        else:
            provider = "none"

    info = {"provider": provider, "model": None, "available": False}

    if provider == "bedrock":
        info["model"] = os.environ.get(
            "BEDROCK_MODEL", "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        info["available"] = has_bedrock_credentials()
    elif provider == "anthropic":
        info["model"] = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        info["available"] = bool(os.environ.get("ANTHROPIC_API_KEY"))

    return info


def switch_provider(provider_name: str, model: str | None = None) -> bool:
    """Switch to a different LLM provider at runtime.
    
    Args:
        provider_name: Name of provider ('bedrock' or 'anthropic')
        model: Optional model override
        
    Returns:
        True if switch successful, False if credentials not available
    """
    provider = provider_name.lower()

    if provider == "bedrock":
        if not has_bedrock_credentials():
            return False
        os.environ["LLM_PROVIDER"] = "bedrock"
        if model:
            os.environ["BEDROCK_MODEL"] = model
        return True

    elif provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        os.environ["LLM_PROVIDER"] = "anthropic"
        if model:
            os.environ["ANTHROPIC_MODEL"] = model
        return True

    return False
