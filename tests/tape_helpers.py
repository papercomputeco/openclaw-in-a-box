"""Shared helpers for creating test Tapes databases.

Matches the real Tapes schema: 11 columns in the nodes table.
Content is stored as JSON arrays of content blocks.
"""
import json
import sqlite3
from pathlib import Path

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS nodes (
    hash TEXT PRIMARY KEY,
    role TEXT,
    content TEXT,
    created_at TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    cache_creation_input_tokens INTEGER DEFAULT 0,
    cache_read_input_tokens INTEGER DEFAULT 0,
    parent_hash TEXT,
    model TEXT,
    agent_name TEXT
)
"""


def create_test_db(db_path: Path) -> sqlite3.Connection:
    """Create a tapes.sqlite with the real schema."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def insert_node(
    conn: sqlite3.Connection,
    *,
    hash: str,
    role: str = "user",
    text: str = "",
    parent_hash: str | None = None,
    model: str | None = None,
    created_at: str = "2026-03-20T10:00:00Z",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    tool_uses: list[dict] | None = None,
    tool_results: list[dict] | None = None,
    is_error: bool = False,
) -> None:
    """Insert a node with properly formatted JSON content."""
    blocks: list[dict] = []
    if text:
        blocks.append({"type": "text", "text": text})
    if tool_uses:
        for tu in tool_uses:
            blocks.append({
                "type": "tool_use",
                "tool_use_id": tu.get("id", ""),
                "tool_name": tu.get("name", ""),
                "tool_input": tu.get("input", {}),
            })
    if tool_results:
        for tr in tool_results:
            blocks.append({
                "type": "tool_result",
                "tool_use_id": tr.get("tool_use_id", ""),
                "content": tr.get("content", ""),
                "is_error": tr.get("is_error", is_error),
            })

    content_json = json.dumps(blocks) if blocks else None
    conn.execute(
        "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            hash, role, content_json, created_at,
            prompt_tokens, completion_tokens, 0, 0,
            parent_hash, model, None,
        ),
    )
    conn.commit()
