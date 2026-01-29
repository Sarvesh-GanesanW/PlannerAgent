"""Configuration management for Planning Agent.

Handles loading and saving of user configuration including LLM provider settings,
API keys, and model preferences. Configuration, logs, and sessions are stored at:
~/.config/plan-agent/ (config.json, agent.log, sessions/)
"""

import json
import os
from getpass import getpass
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "plan-agent"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "provider": "bedrock",
    "bedrock_model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "anthropic_model": "claude-sonnet-4-5-20250929",
}


def load_config():
    """Load configuration from file or return defaults.
    
    Returns:
        Dict containing merged configuration (defaults + user settings)
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to file.
    
    Args:
        config: Dictionary containing configuration to save
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def has_bedrock_credentials():
    """Check if Bedrock credentials are available (API key, AWS creds, or IAM role)."""
    config = load_config()

    if config.get("bedrock_api_key"):
        return True
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return True

    if config.get("aws_access_key_id") and config.get("aws_secret_access_key"):
        return True

    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return True

    if os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"):
        return True
    if os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE"):
        return True

    try:
        import socket
        import urllib.request

        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(1)

        try:
            req = urllib.request.Request(
                "http://169.254.169.254/latest/meta-data/iam/security-credentials/", method="GET"
            )
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    socket.setdefaulttimeout(original_timeout)
                    return True
        except Exception:
            pass
        finally:
            socket.setdefaulttimeout(original_timeout)
    except Exception:
        pass

    return False


def is_configured():
    """Check if LLM provider is properly configured.
    
    Returns:
        True if provider has valid credentials, False otherwise
    """
    config = load_config()
    provider = config.get("provider", "bedrock")

    if provider == "bedrock":
        return has_bedrock_credentials()
    elif provider == "anthropic":
        return bool(config.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY"))
    return False


def interactive_setup():
    """Run interactive configuration wizard for LLM provider setup.
    
    Prompts user to select provider, enter credentials, and choose model.
    Saves configuration to ~/.config/plan-agent/config.json
    
    Returns:
        Dict containing the configured settings
    """
    print("\n🤖 Plan Agent Configuration\n")
    print("Select LLM Provider:")
    print("  1) Amazon Bedrock (Claude via AWS)")
    print("  2) Anthropic (Claude 4.5)")

    choice = input("\nChoice (1-2) [1]: ").strip() or "1"

    config = load_config()

    if choice == "1":
        config["provider"] = "bedrock"
        print("\n🔑 Amazon Bedrock Configuration")

        region = input("AWS Region [us-east-1]: ").strip() or "us-east-1"
        config["aws_region"] = region

        print("\nAuthentication Method:")
        print("  1) Bedrock API Key (recommended, easiest)")
        print("  2) AWS Credentials (Access Key + Secret)")
        auth_choice = input("Choice (1-2) [1]: ").strip() or "1"

        if auth_choice == "1":
            print("\nEnter your Bedrock API Key (starts with ABSK...):")
            api_key = getpass("Bedrock API Key: ").strip()
            if api_key:
                config["bedrock_api_key"] = api_key
        else:
            print("\nAWS Credentials:")
            access_key = input("AWS Access Key ID: ").strip()
            if access_key:
                config["aws_access_key_id"] = access_key
                secret_key = getpass("AWS Secret Access Key: ").strip()
                if secret_key:
                    config["aws_secret_access_key"] = secret_key

        print("\nSelect model:")
        print("  1) Claude 4.5 Sonnet (recommended, best balance)")
        print("  2) Claude 4.5 Opus (most powerful)")
        model_choice = input("Choice (1-2) [1]: ").strip() or "1"

        if model_choice == "2":
            config["bedrock_model"] = "global.anthropic.claude-opus-4-5-20251101-v1:0"
        else:
            config["bedrock_model"] = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

    else:
        config["provider"] = "anthropic"
        print("\n🔑 Anthropic Configuration")
        config["anthropic_api_key"] = getpass("API Key (sk-ant-...): ").strip()

        print("\nSelect model:")
        print("  1) claude-sonnet-4-5-20250929 (recommended, best balance)")
        print("  2) claude-opus-4-5-20251101 (most powerful)")
        model_choice = input("Choice (1-2) [1]: ").strip() or "1"

        if model_choice == "2":
            config["anthropic_model"] = "claude-opus-4-5-20251101"
        else:
            config["anthropic_model"] = "claude-sonnet-4-5-20250929"

    save_config(config)
    print(f"\n✅ Saved to {CONFIG_FILE}\n")

    if config["provider"] == "bedrock":
        os.environ["AWS_REGION"] = config.get("aws_region", "us-east-1")
        if config.get("bedrock_api_key"):
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = config["bedrock_api_key"]
        if config.get("aws_access_key_id"):
            os.environ["AWS_ACCESS_KEY_ID"] = config["aws_access_key_id"]
        if config.get("aws_secret_access_key"):
            os.environ["AWS_SECRET_ACCESS_KEY"] = config["aws_secret_access_key"]
        os.environ["LLM_PROVIDER"] = "bedrock"
    else:
        os.environ["ANTHROPIC_API_KEY"] = config["anthropic_api_key"]
        os.environ["LLM_PROVIDER"] = "anthropic"

    return config


def get_credentials(provider):
    """Get credentials for the specified provider."""
    config = load_config()

    if provider == "bedrock":
        return {
            "region": os.environ.get("AWS_REGION") or config.get("aws_region", "us-east-1"),
            "api_key": os.environ.get("AWS_BEARER_TOKEN_BEDROCK") or config.get("bedrock_api_key"),
            "access_key_id": os.environ.get("AWS_ACCESS_KEY_ID") or config.get("aws_access_key_id"),
            "secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY")
            or config.get("aws_secret_access_key"),
        }
    elif provider == "anthropic":
        return {"api_key": os.environ.get("ANTHROPIC_API_KEY") or config.get("anthropic_api_key")}

    return None


def get_api_key(provider):
    """Deprecated: Use get_credentials() instead."""
    creds = get_credentials(provider)
    if creds and "api_key" in creds:
        return creds["api_key"]
    return None
