"""Session persistence and management for Planning Agent.

Sessions are stored as compressed pickle files in ~/.config/plan-agent/sessions/
"""

import gzip
import json
import pickle
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import tiktoken
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from config import CONFIG_DIR

SESSIONS_DIR = CONFIG_DIR / "sessions"
MAX_STORED_MESSAGES = 20
TOKEN_LIMIT = 8000
COMPRESSION_THRESHOLD = 0.7


class MessageSerializer:
    """Handles serialization and deserialization of messages."""

    def serialize(self, msg: BaseMessage) -> dict[str, Any]:
        """Serialize a message to a dictionary."""
        base = {"type": msg.type, "content": msg.content}

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            base["tool_calls"] = msg.tool_calls
        if hasattr(msg, "tool_call_id"):
            base["tool_call_id"] = msg.tool_call_id
        if hasattr(msg, "name"):
            base["name"] = msg.name

        return base

    def deserialize(self, data: dict[str, Any]) -> BaseMessage:
        """Deserialize a dictionary to a message."""
        msg_type = data.get("type", "human")
        content = data.get("content", "")

        if msg_type == "human":
            return HumanMessage(content=content)
        elif msg_type == "ai":
            msg = AIMessage(content=content)
            if "tool_calls" in data:
                msg.tool_calls = data["tool_calls"]
            return msg
        elif msg_type == "system":
            return SystemMessage(content=content)
        elif msg_type == "tool":
            return ToolMessage(
                content=content,
                tool_call_id=data.get("tool_call_id", ""),
                name=data.get("name", ""),
            )
        return HumanMessage(content=content)


class TokenCounter:
    """Count tokens in messages."""

    def __init__(self, model: str = "gpt-4"):
        self._encoding = self._get_encoding(model)

    def _get_encoding(self, model: str):
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self._encoding.encode(text))

    def count_messages(self, messages: list[BaseMessage]) -> int:
        """Count total tokens in list of messages.

        Args:
            messages: List of messages to count

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            if isinstance(msg.content, str):
                total += self.count(msg.content)
            total += self.count(msg.type)
        return total


class SessionCompactor:
    """Compact session state to reduce size."""

    def __init__(self, token_counter: TokenCounter | None = None):
        self._counter = token_counter or TokenCounter()

    def compact(self, state: dict[str, Any]) -> dict[str, Any]:
        """Compact session state before saving."""
        state = self._compact_messages(state)
        state = self._compact_undo_stacks(state)
        state = self._compact_plan_history(state)
        return state

    def _compact_messages(self, state: dict[str, Any]) -> dict[str, Any]:
        """Keep only recent messages, summarize older ones."""
        messages = state.get("messages", [])

        if len(messages) <= MAX_STORED_MESSAGES:
            return state

        # Keep last N messages
        recent_messages = messages[-MAX_STORED_MESSAGES:]

        # Summarize older messages
        older_messages = messages[:-MAX_STORED_MESSAGES]
        summary = self._summarize_messages(older_messages)

        # Store summary separately
        state["message_summary"] = summary
        state["messages"] = recent_messages
        state["total_message_count"] = len(messages)

        return state

    def _summarize_messages(self, messages: list[BaseMessage]) -> str:
        """Create a summary of older messages."""
        parts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content[:100] if len(msg.content) > 100 else msg.content
                parts.append(f"User: {content}")
            elif isinstance(msg, AIMessage):
                parts.append("Assistant: [responded]")
        return " | ".join(parts[-10:])  # Keep last 10 interactions

    def _compact_undo_stacks(self, state: dict[str, Any]) -> dict[str, Any]:
        """Limit undo/redo stack size."""
        MAX_STACK = 10

        if len(state.get("undo_stack", [])) > MAX_STACK:
            state["undo_stack"] = state["undo_stack"][-MAX_STACK:]

        if len(state.get("redo_stack", [])) > MAX_STACK:
            state["redo_stack"] = state["redo_stack"][-MAX_STACK:]

        return state

    def _compact_plan_history(self, state: dict[str, Any]) -> dict[str, Any]:
        """Keep only last N plan history entries."""
        MAX_HISTORY = 5

        plan = state.get("current_plan", {})
        history = plan.get("history", [])

        if len(history) > MAX_HISTORY:
            plan["history"] = history[-MAX_HISTORY:]
            plan["_full_history_count"] = len(history)

        return state

    def should_compact(self, state: dict[str, Any]) -> bool:
        """Check if state should be compacted based on token count."""
        messages = state.get("messages", [])
        token_count = self._counter.count_messages(messages)
        return token_count > TOKEN_LIMIT * COMPRESSION_THRESHOLD


class SessionStorage:
    """Handles low-level session storage operations with compression."""

    def __init__(self, base_dir: Path = SESSIONS_DIR):
        self._base_dir = base_dir
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, session_id: str) -> Path:
        return self._base_dir / f"{session_id}.json.gz"

    def exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: Session ID to check

        Returns:
            True if session exists, False otherwise
        """
        return self._get_filepath(session_id).exists()

    def save(self, session_id: str, data: dict[str, Any]) -> None:
        """Save session with gzip compression."""
        filepath = self._get_filepath(session_id)

        # Use msgpack + gzip for efficiency
        serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = gzip.compress(serialized, compresslevel=6)

        with open(filepath, "wb") as f:
            f.write(compressed)

    def load(self, session_id: str) -> dict[str, Any] | None:
        """Load session from gzip compressed file."""
        filepath = self._get_filepath(session_id)
        if not filepath.exists():
            # Try old JSON format for migration
            old_filepath = self._base_dir / f"{session_id}.json"
            if old_filepath.exists():
                return self._load_old_format(old_filepath)
            return None

        with open(filepath, "rb") as f:
            compressed = f.read()

        serialized = gzip.decompress(compressed)
        return pickle.loads(serialized)

    def _load_old_format(self, filepath: Path) -> dict[str, Any] | None:
        """Load old JSON format and migrate."""
        try:
            with open(filepath) as f:
                return json.load(f)
        except Exception:
            return None

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        filepath = self._get_filepath(session_id)
        if filepath.exists():
            filepath.unlink()
            return True

        # Try old format
        old_filepath = self._base_dir / f"{session_id}.json"
        if old_filepath.exists():
            old_filepath.unlink()
            return True

        return False

    def list_all(self) -> list[Path]:
        """List all session files."""
        sessions = list(self._base_dir.glob("*.json.gz"))
        sessions.extend(self._base_dir.glob("*.json"))  # Include old format
        return sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)

    def get_size(self, session_id: str) -> int:
        """Get file size in bytes."""
        filepath = self._get_filepath(session_id)
        if filepath.exists():
            return filepath.stat().st_size
        return 0


class SessionManager:
    """Manages conversation sessions with full CRUD operations."""

    def __init__(
        self,
        storage: SessionStorage | None = None,
        serializer: MessageSerializer | None = None,
        compactor: SessionCompactor | None = None,
    ):
        self._storage = storage or SessionStorage()
        self._serializer = serializer or MessageSerializer()
        self._compactor = compactor or SessionCompactor()

    def save(
        self,
        session_id: str,
        state: dict[str, Any],
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Save a conversation session to disk with automatic compaction."""
        # Check if compaction needed
        if self._compactor.should_compact(state):
            state = self._compactor.compact(state)

        timestamp = datetime.now().isoformat()

        # Serialize messages
        messages = [self._serializer.serialize(msg) for msg in state.get("messages", [])]

        session_data = {
            "session_id": session_id,
            "title": title or f"Session {session_id[:8]}",
            "created_at": state.get("created_at", timestamp),
            "updated_at": timestamp,
            "tags": tags or [],
            "messages": messages,
            "message_summary": state.get("message_summary", ""),
            "total_message_count": state.get("total_message_count", len(messages)),
            "summary": state.get("summary", ""),
            "current_plan": state.get("current_plan", {}),
            "conversation_turn": state.get("conversation_turn", 0),
            "user_preferences": state.get("user_preferences", {}),
            "last_action": state.get("last_action", ""),
            "undo_stack": state.get("undo_stack", []),
            "redo_stack": state.get("redo_stack", []),
            "version": 2,  # Session format version
        }

        self._storage.save(session_id, session_data)
        return session_id

    def load(self, session_id: str) -> dict[str, Any] | None:
        """Load a conversation session from disk."""
        session_data = self._storage.load(session_id)
        if not session_data:
            return None

        # Deserialize messages
        messages = [self._serializer.deserialize(msg) for msg in session_data.get("messages", [])]

        return {
            "messages": messages,
            "message_summary": session_data.get("message_summary", ""),
            "total_message_count": session_data.get("total_message_count", len(messages)),
            "summary": session_data.get("summary", ""),
            "current_plan": session_data.get("current_plan", {}),
            "conversation_turn": session_data.get("conversation_turn", 0),
            "user_preferences": session_data.get("user_preferences", {}),
            "last_action": session_data.get("last_action", ""),
            "undo_stack": session_data.get("undo_stack", []),
            "redo_stack": session_data.get("redo_stack", []),
            "created_at": session_data.get("created_at"),
            "updated_at": session_data.get("updated_at"),
            "session_id": session_id,
            "tags": session_data.get("tags", []),
        }

    def compact_session(self, session_id: str) -> bool:
        """Manually compact a session."""
        state = self.load(session_id)
        if not state:
            return False

        title = state.get("current_plan", {}).get("title")
        tags = state.get("tags", [])

        # Force compaction
        state = self._compactor.compact(state)

        self.save(session_id, state, title=title, tags=tags)
        return True

    def get_session_size(self, session_id: str) -> int:
        """Get session file size in bytes."""
        return self._storage.get_size(session_id)

    def list_sessions(self, tags: list[str] | None = None) -> list[dict[str, Any]]:
        """List all saved sessions with optional tag filtering."""
        sessions = []

        for filepath in self._storage.list_all():
            try:
                if filepath.suffix == ".gz":
                    data = self._storage.load(filepath.stem.replace(".json", ""))
                else:
                    with open(filepath) as f:
                        data = json.load(f)

                if not data:
                    continue

                if tags:
                    session_tags = set(data.get("tags", []))
                    if not any(tag in session_tags for tag in tags):
                        continue

                file_size = filepath.stat().st_size

                sessions.append(
                    {
                        "session_id": data.get("session_id", filepath.stem.replace(".json", "")),
                        "title": data.get("title", "Untitled"),
                        "created_at": data.get("created_at", "Unknown"),
                        "updated_at": data.get("updated_at", "Unknown"),
                        "tags": data.get("tags", []),
                        "message_count": data.get(
                            "total_message_count", len(data.get("messages", []))
                        ),
                        "has_plan": bool(data.get("current_plan", {}).get("steps", [])),
                        "size_bytes": file_size,
                        "size_kb": round(file_size / 1024, 1),
                    }
                )
            except Exception:
                continue

        return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a session by ID."""
        return self._storage.delete(session_id)

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search sessions by title, plan content, or tags."""
        query_lower = query.lower()
        matches = []

        for filepath in self._storage.list_all():
            try:
                if filepath.suffix == ".gz":
                    data = self._storage.load(filepath.stem.replace(".json", ""))
                else:
                    with open(filepath) as f:
                        data = json.load(f)

                if not data:
                    continue

                match_reason = self._get_match_reason(data, query_lower)
                if match_reason:
                    file_size = filepath.stat().st_size
                    matches.append(
                        {
                            "session_id": data.get(
                                "session_id", filepath.stem.replace(".json", "")
                            ),
                            "title": data.get("title", "Untitled"),
                            "updated_at": data.get("updated_at", "Unknown"),
                            "tags": data.get("tags", []),
                            "match_reason": match_reason,
                            "size_kb": round(file_size / 1024, 1),
                        }
                    )
            except Exception:
                continue

        return sorted(matches, key=lambda x: x["updated_at"], reverse=True)

    def _get_match_reason(self, data: dict[str, Any], query_lower: str) -> str | None:
        """Determine why a session matches a query."""
        if query_lower in data.get("title", "").lower():
            return "title"

        tags = data.get("tags", [])
        if any(query_lower in tag.lower() for tag in tags):
            return "tag"

        plan = data.get("current_plan", {})
        plan_text = json.dumps(plan).lower()
        if query_lower in plan_text:
            return "plan content"

        summary = data.get("message_summary", "")
        if query_lower in summary.lower():
            return "message summary"

        return None

    def auto_save(self, state: dict[str, Any]) -> str:
        """Auto-save current session if it has a session_id."""
        session_id = state.get("session_id")
        if not session_id:
            session_id = self.create_session_id()
            state["session_id"] = session_id

        # Get title from plan if available
        title = None
        if state.get("current_plan"):
            title = state["current_plan"].get("title")

        self.save(session_id, state, title=title)
        return session_id

    def fork(self, session_id: str, new_title: str | None = None) -> str | None:
        """Create a copy of an existing session with a new ID."""
        state = self.load(session_id)
        if not state:
            return None

        new_id = self.create_session_id()
        state["session_id"] = new_id
        state["conversation_turn"] = 0
        state["title"] = new_title or f"{state.get('title', 'Fork')} (Copy)"
        state["undo_stack"] = []
        state["redo_stack"] = []
        state["message_summary"] = ""
        state["total_message_count"] = len(state.get("messages", []))

        self.save(new_id, state, title=state["title"])
        return new_id

    @staticmethod
    def create_session_id() -> str:
        """Generate a new unique session ID."""
        return str(uuid.uuid4())[:12]


class SessionOperations:
    """High-level session operations for CLI integration."""

    def __init__(self, manager: SessionManager | None = None):
        self._manager = manager or SessionManager()

    def resume_session(self, session_id: str) -> dict[str, Any] | None:
        """Resume a session by ID."""
        return self._manager.load(session_id)

    def list_recent(self, limit: int = 10, tags: list[str] | None = None) -> list[dict[str, Any]]:
        """List recent sessions."""
        sessions = self._manager.list_sessions(tags=tags)
        return sessions[:limit]

    def search_sessions(self, query: str) -> list[dict[str, Any]]:
        """Search for sessions."""
        return self._manager.search(query)

    def tag_session(self, session_id: str, tags: list[str]) -> bool:
        """Add tags to an existing session."""
        state = self._manager.load(session_id)
        if not state:
            return False

        current_tags = set(state.get("tags", []))
        current_tags.update(tags)

        self._manager.save(session_id, state, tags=list(current_tags))
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self._manager.delete(session_id)

    def compact_session(self, session_id: str) -> bool:
        """Manually compact a session."""
        return self._manager.compact_session(session_id)
