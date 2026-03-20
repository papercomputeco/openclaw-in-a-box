"""Tests for tape_reader.py -- the stdlib-only Tapes SQLite reader."""

import json
import sqlite3
from pathlib import Path

import pytest

from tape_helpers import create_test_db, insert_node
from tape_reader import (
    TapeEntry,
    TapeReader,
    TapeSession,
    TokenUsage,
    ToolResult,
    ToolUse,
    _parse_content_blob,
    _summarize_tool_input,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "tapes.sqlite"


@pytest.fixture()
def empty_db(db_path: Path) -> tuple[Path, sqlite3.Connection]:
    conn = create_test_db(db_path)
    return db_path, conn


# ---------------------------------------------------------------------------
# Dataclass defaults
# ---------------------------------------------------------------------------


class TestTapeEntryDefaults:
    def test_default_fields(self):
        entry = TapeEntry()
        assert entry.type == ""
        assert entry.timestamp == ""
        assert entry.session_id == ""
        assert entry.text_content == ""
        assert entry.tool_uses == []
        assert entry.tool_results == []
        assert entry.raw == {}

    def test_default_token_usage(self):
        entry = TapeEntry()
        assert entry.token_usage.input_tokens == 0
        assert entry.token_usage.output_tokens == 0
        assert entry.token_usage.cache_creation == 0
        assert entry.token_usage.cache_read == 0

    def test_tool_use_defaults(self):
        tu = ToolUse()
        assert tu.id == ""
        assert tu.name == ""
        assert tu.input_summary == ""

    def test_tool_result_defaults(self):
        tr = ToolResult()
        assert tr.tool_use_id == ""
        assert tr.content_summary == ""
        assert tr.is_error is False

    def test_token_usage_defaults(self):
        tok = TokenUsage()
        assert tok.input_tokens == 0
        assert tok.output_tokens == 0
        assert tok.cache_creation == 0
        assert tok.cache_read == 0

    def test_tape_session_defaults(self):
        session = TapeSession()
        assert session.session_id == ""
        assert session.entries == []
        assert session.start_time == ""
        assert session.end_time == ""


# ---------------------------------------------------------------------------
# list_sessions()
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_empty_db_returns_empty(self, empty_db):
        db_path, _ = empty_db
        reader = TapeReader(str(db_path))
        assert reader.list_sessions() == []

    def test_single_root(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="hello")
        reader = TapeReader(str(db_path))
        assert reader.list_sessions() == ["root1"]

    def test_multiple_roots_ordered_by_time(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root2", role="user", text="b", created_at="2026-03-20T12:00:00Z")
        insert_node(conn, hash="root1", role="user", text="a", created_at="2026-03-20T10:00:00Z")
        reader = TapeReader(str(db_path))
        assert reader.list_sessions() == ["root1", "root2"]

    def test_child_nodes_not_in_list(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="root")
        insert_node(conn, hash="child1", role="assistant", text="response",
                    parent_hash="root1", created_at="2026-03-20T10:01:00Z")
        reader = TapeReader(str(db_path))
        sessions = reader.list_sessions()
        assert sessions == ["root1"]
        assert "child1" not in sessions


# ---------------------------------------------------------------------------
# read_session()
# ---------------------------------------------------------------------------


class TestReadSession:
    def test_single_node_session(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="Hello")
        reader = TapeReader(str(db_path))
        session = reader.read_session("root1")
        assert isinstance(session, TapeSession)
        assert session.session_id == "root1"
        assert len(session.entries) == 1
        assert session.entries[0].type == "user"
        assert session.entries[0].text_content == "Hello"

    def test_session_start_and_end_time(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="start",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="child1", role="assistant", text="middle",
                    parent_hash="root1", created_at="2026-03-20T10:01:00Z")
        insert_node(conn, hash="child2", role="user", text="end",
                    parent_hash="child1", created_at="2026-03-20T10:02:00Z")
        reader = TapeReader(str(db_path))
        session = reader.read_session("root1")
        assert session.start_time == "2026-03-20T10:00:00Z"
        assert session.end_time == "2026-03-20T10:02:00Z"

    def test_empty_session_no_times(self, empty_db):
        db_path, conn = empty_db
        # root exists but no chain from it in the DB would give empty rows
        # We test the case when read_session is called on unknown hash
        reader = TapeReader(str(db_path))
        session = reader.read_session("nonexistent")
        assert session.session_id == "nonexistent"
        assert session.entries == []
        assert session.start_time == ""
        assert session.end_time == ""

    def test_chain_ordered_by_time(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="first",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="child1", role="assistant", text="second",
                    parent_hash="root1", created_at="2026-03-20T10:01:00Z")
        insert_node(conn, hash="child2", role="user", text="third",
                    parent_hash="child1", created_at="2026-03-20T10:02:00Z")
        reader = TapeReader(str(db_path))
        session = reader.read_session("root1")
        assert len(session.entries) == 3
        assert session.entries[0].text_content == "first"
        assert session.entries[1].text_content == "second"
        assert session.entries[2].text_content == "third"

    def test_assistant_token_usage(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="question")
        insert_node(conn, hash="child1", role="assistant", text="answer",
                    parent_hash="root1",
                    prompt_tokens=100,
                    completion_tokens=50,
                    created_at="2026-03-20T10:01:00Z")
        reader = TapeReader(str(db_path))
        session = reader.read_session("root1")
        asst = session.entries[1]
        assert asst.token_usage.input_tokens == 100
        assert asst.token_usage.output_tokens == 50

    def test_raw_dict_populated(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="hello",
                    model="claude-3-5-sonnet")
        reader = TapeReader(str(db_path))
        session = reader.read_session("root1")
        raw = session.entries[0].raw
        assert raw["hash"] == "root1"
        assert raw["role"] == "user"
        assert raw["parent_hash"] is None


# ---------------------------------------------------------------------------
# iter_entries()
# ---------------------------------------------------------------------------


class TestIterEntries:
    def test_generator_yields_entries(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="msg1")
        insert_node(conn, hash="child1", role="assistant", text="msg2",
                    parent_hash="root1", created_at="2026-03-20T10:01:00Z")
        reader = TapeReader(str(db_path))
        entries = list(reader.iter_entries("root1"))
        assert len(entries) == 2
        assert entries[0].text_content == "msg1"
        assert entries[1].text_content == "msg2"

    def test_generator_is_lazy(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="hello")
        reader = TapeReader(str(db_path))
        gen = reader.iter_entries("root1")
        # Should be a generator, not a list
        import types
        assert isinstance(gen, types.GeneratorType)

    def test_iter_empty_session(self, empty_db):
        db_path, _ = empty_db
        reader = TapeReader(str(db_path))
        entries = list(reader.iter_entries("nonexistent"))
        assert entries == []


# ---------------------------------------------------------------------------
# Tool use parsing
# ---------------------------------------------------------------------------


class TestToolUseParsing:
    def _make_assistant_with_tool(self, empty_db, tool_name, tool_input):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="go")
        insert_node(conn, hash="child1", role="assistant",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    tool_uses=[{"id": "tu1", "name": tool_name, "input": tool_input}])
        return db_path

    def test_read_tool_summary(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "Read", {"file_path": "/some/file.py"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.name == "Read"
        assert tu.input_summary == "/some/file.py"

    def test_bash_tool_summary(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "Bash", {"command": "ls -la /tmp"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.name == "Bash"
        assert tu.input_summary == "ls -la /tmp"

    def test_grep_tool_summary(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "Grep", {"pattern": "def foo"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.name == "Grep"
        assert tu.input_summary == "pattern=def foo"

    def test_glob_tool_summary(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "Glob", {"pattern": "**/*.py"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.name == "Glob"
        assert tu.input_summary == "pattern=**/*.py"

    def test_agent_tool_summary(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "Agent", {"description": "Search for patterns"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.name == "Agent"
        assert tu.input_summary == "Search for patterns"

    def test_unknown_tool_with_prompt_key(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "SomeTool", {"prompt": "do something"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.name == "SomeTool"
        assert tu.input_summary == "prompt=do something"

    def test_unknown_tool_with_query_key(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "SearchTool", {"query": "my query"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.input_summary == "query=my query"

    def test_unknown_tool_with_description_key(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "UnknownTool", {"description": "a description"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.input_summary == "description=a description"

    def test_unknown_tool_with_command_key(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "UnknownTool", {"command": "run me"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.input_summary == "command=run me"

    def test_unknown_tool_with_file_path_key(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "UnknownTool", {"file_path": "/some/path"}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        assert tu.input_summary == "file_path=/some/path"

    def test_unknown_tool_no_known_keys(self, empty_db):
        db_path = self._make_assistant_with_tool(
            empty_db, "UnknownTool", {"foo": "bar", "baz": 42}
        )
        session = TapeReader(str(db_path)).read_session("root1")
        tu = session.entries[1].tool_uses[0]
        # Falls back to str(tool_input)[:200]
        assert "foo" in tu.input_summary or "baz" in tu.input_summary

    def test_tool_use_id_preserved(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="go")
        insert_node(conn, hash="child1", role="assistant",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    tool_uses=[{"id": "my-tool-id-123", "name": "Bash",
                                "input": {"command": "ls"}}])
        session = TapeReader(str(db_path)).read_session("root1")
        assert session.entries[1].tool_uses[0].id == "my-tool-id-123"

    def test_multiple_tool_uses(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="go")
        insert_node(conn, hash="child1", role="assistant",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    tool_uses=[
                        {"id": "tu1", "name": "Read", "input": {"file_path": "/a.py"}},
                        {"id": "tu2", "name": "Bash", "input": {"command": "echo hi"}},
                    ])
        session = TapeReader(str(db_path)).read_session("root1")
        tus = session.entries[1].tool_uses
        assert len(tus) == 2
        assert tus[0].name == "Read"
        assert tus[1].name == "Bash"


# ---------------------------------------------------------------------------
# Tool result parsing
# ---------------------------------------------------------------------------


class TestToolResultParsing:
    def test_normal_tool_result(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user",
                    tool_results=[{
                        "tool_use_id": "tu1",
                        "content": "file contents here",
                        "is_error": False,
                    }])
        session = TapeReader(str(db_path)).read_session("root1")
        tr = session.entries[0].tool_results[0]
        assert tr.tool_use_id == "tu1"
        assert tr.content_summary == "file contents here"
        assert tr.is_error is False

    def test_error_tool_result(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user",
                    tool_results=[{
                        "tool_use_id": "tu2",
                        "content": "command not found",
                        "is_error": True,
                    }])
        session = TapeReader(str(db_path)).read_session("root1")
        tr = session.entries[0].tool_results[0]
        assert tr.is_error is True
        assert tr.content_summary == "command not found"

    def test_list_type_tool_result_content(self, empty_db):
        db_path, conn = empty_db
        # Manually insert a node with list-type tool_result content
        content = json.dumps([{
            "type": "tool_result",
            "tool_use_id": "tu3",
            "content": [
                {"text": "line one"},
                {"text": "line two"},
            ],
            "is_error": False,
        }])
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                hash TEXT PRIMARY KEY, role TEXT, content TEXT, created_at TEXT,
                prompt_tokens INTEGER DEFAULT 0, completion_tokens INTEGER DEFAULT 0,
                cache_creation_input_tokens INTEGER DEFAULT 0,
                cache_read_input_tokens INTEGER DEFAULT 0,
                parent_hash TEXT, model TEXT, agent_name TEXT
            )
        """)
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "user", content, "2026-03-20T10:00:00Z", 0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        conn.close()
        session = TapeReader(str(db_path)).read_session("root1")
        tr = session.entries[0].tool_results[0]
        assert "line one" in tr.content_summary
        assert "line two" in tr.content_summary

    def test_content_summary_truncated_to_500(self, empty_db):
        db_path, conn = empty_db
        long_content = "x" * 600
        insert_node(conn, hash="root1", role="user",
                    tool_results=[{
                        "tool_use_id": "tu1",
                        "content": long_content,
                        "is_error": False,
                    }])
        session = TapeReader(str(db_path)).read_session("root1")
        tr = session.entries[0].tool_results[0]
        assert len(tr.content_summary) == 500

    def test_multiple_tool_results(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user",
                    tool_results=[
                        {"tool_use_id": "tu1", "content": "result one", "is_error": False},
                        {"tool_use_id": "tu2", "content": "result two", "is_error": True},
                    ])
        session = TapeReader(str(db_path)).read_session("root1")
        trs = session.entries[0].tool_results
        assert len(trs) == 2
        assert trs[0].content_summary == "result one"
        assert trs[1].is_error is True


# ---------------------------------------------------------------------------
# NULL content handling
# ---------------------------------------------------------------------------


class TestNullContentHandling:
    def test_null_content_gives_empty_entry(self, empty_db):
        db_path, conn = empty_db
        # Insert with no text or tool data -> content_json is None
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "user", None, "2026-03-20T10:00:00Z", 0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        entry = session.entries[0]
        assert entry.text_content == ""
        assert entry.tool_uses == []
        assert entry.tool_results == []

    def test_null_role_defaults_to_empty(self, empty_db):
        db_path, conn = empty_db
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", None, None, "2026-03-20T10:00:00Z", 0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        assert session.entries[0].type == ""

    def test_null_created_at_defaults_to_empty(self, empty_db):
        db_path, conn = empty_db
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "user", None, None, 0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        assert session.entries[0].timestamp == ""


# ---------------------------------------------------------------------------
# Invalid JSON content handling
# ---------------------------------------------------------------------------


class TestInvalidJsonContent:
    def test_invalid_json_gives_empty_content(self, empty_db):
        db_path, conn = empty_db
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "user", "not valid json{{", "2026-03-20T10:00:00Z",
             0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        entry = session.entries[0]
        assert entry.text_content == ""
        assert entry.tool_uses == []

    def test_json_object_not_list_gives_empty(self, empty_db):
        db_path, conn = empty_db
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "user", '{"key": "value"}', "2026-03-20T10:00:00Z",
             0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        assert session.entries[0].text_content == ""

    def test_json_list_with_non_dict_items_filtered(self, empty_db):
        db_path, conn = empty_db
        content = json.dumps([
            {"type": "text", "text": "hello"},
            "a string, not a dict",
            42,
            {"type": "text", "text": "world"},
        ])
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "user", content, "2026-03-20T10:00:00Z",
             0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        # Only dict items processed; text blocks collected
        assert "hello" in session.entries[0].text_content
        assert "world" in session.entries[0].text_content


# ---------------------------------------------------------------------------
# _parse_content_blob unit tests
# ---------------------------------------------------------------------------


class TestParseContentBlob:
    def test_none_returns_empty(self):
        assert _parse_content_blob(None) == []

    def test_valid_json_list(self):
        blob = json.dumps([{"type": "text", "text": "hi"}])
        result = _parse_content_blob(blob)
        assert result == [{"type": "text", "text": "hi"}]

    def test_invalid_json_returns_empty(self):
        assert _parse_content_blob("{{invalid") == []

    def test_json_object_not_list_returns_empty(self):
        assert _parse_content_blob('{"k": "v"}') == []

    def test_filters_non_dict_items(self):
        blob = json.dumps([{"type": "text"}, "string", 42, None])
        result = _parse_content_blob(blob)
        assert result == [{"type": "text"}]

    def test_bytes_input(self):
        blob = json.dumps([{"type": "text", "text": "bytes"}]).encode()
        result = _parse_content_blob(blob)
        assert result == [{"type": "text", "text": "bytes"}]


# ---------------------------------------------------------------------------
# _summarize_tool_input unit tests
# ---------------------------------------------------------------------------


class TestSummarizeToolInput:
    def test_read(self):
        assert _summarize_tool_input("Read", {"file_path": "/a/b.py"}) == "/a/b.py"

    def test_write(self):
        assert _summarize_tool_input("Write", {"file_path": "/out.txt"}) == "/out.txt"

    def test_edit(self):
        assert _summarize_tool_input("Edit", {"file_path": "/edit.py"}) == "/edit.py"

    def test_bash(self):
        assert _summarize_tool_input("Bash", {"command": "echo hi"}) == "echo hi"

    def test_bash_truncates_at_200(self):
        long_cmd = "x" * 300
        result = _summarize_tool_input("Bash", {"command": long_cmd})
        assert len(result) == 200

    def test_grep(self):
        assert _summarize_tool_input("Grep", {"pattern": "foo"}) == "pattern=foo"

    def test_glob(self):
        assert _summarize_tool_input("Glob", {"pattern": "**/*.py"}) == "pattern=**/*.py"

    def test_agent(self):
        result = _summarize_tool_input("Agent", {"description": "do stuff"})
        assert result == "do stuff"

    def test_agent_truncates_at_200(self):
        long_desc = "d" * 300
        result = _summarize_tool_input("Agent", {"description": long_desc})
        assert len(result) == 200

    def test_non_dict_tool_input(self):
        result = _summarize_tool_input("Bash", "not a dict")
        assert result == "not a dict"

    def test_non_dict_truncated(self):
        long_str = "y" * 300
        result = _summarize_tool_input("SomeTool", long_str)
        assert len(result) == 200

    def test_unknown_tool_prompt_key(self):
        result = _summarize_tool_input("X", {"prompt": "do it"})
        assert result == "prompt=do it"

    def test_unknown_tool_query_key(self):
        result = _summarize_tool_input("X", {"query": "search"})
        assert result == "query=search"

    def test_unknown_tool_description_key(self):
        result = _summarize_tool_input("X", {"description": "desc"})
        assert result == "description=desc"

    def test_unknown_tool_command_key(self):
        result = _summarize_tool_input("X", {"command": "run"})
        assert result == "command=run"

    def test_unknown_tool_file_path_key(self):
        result = _summarize_tool_input("X", {"file_path": "/p"})
        assert result == "file_path=/p"

    def test_unknown_tool_no_known_key(self):
        result = _summarize_tool_input("X", {"alpha": "beta"})
        assert "alpha" in result or "beta" in result

    def test_unknown_tool_value_truncated(self):
        long_val = "v" * 300
        result = _summarize_tool_input("X", {"prompt": long_val})
        assert len(result) <= 207  # "prompt=" (7) + 200


# ---------------------------------------------------------------------------
# Edge cases: text + tools combined
# ---------------------------------------------------------------------------


class TestCombinedContent:
    def test_assistant_text_and_tool_uses(self, empty_db):
        db_path, conn = empty_db
        insert_node(conn, hash="root1", role="user", text="go")
        # Manually build content with text + tool_use
        content = json.dumps([
            {"type": "text", "text": "I will read the file."},
            {"type": "tool_use", "tool_use_id": "tu1",
             "tool_name": "Read", "tool_input": {"file_path": "/foo.py"}},
        ])
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("child1", "assistant", content, "2026-03-20T10:01:00Z",
             10, 5, 0, 0, "root1", "claude-3", None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        asst = session.entries[1]
        assert asst.text_content == "I will read the file."
        assert len(asst.tool_uses) == 1
        assert asst.tool_uses[0].name == "Read"

    def test_user_text_and_tool_results(self, empty_db):
        db_path, conn = empty_db
        content = json.dumps([
            {"type": "text", "text": "here is the result"},
            {"type": "tool_result", "tool_use_id": "tu1",
             "content": "output text", "is_error": False},
        ])
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "user", content, "2026-03-20T10:00:00Z",
             0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        entry = session.entries[0]
        assert entry.text_content == "here is the result"
        assert len(entry.tool_results) == 1

    def test_assistant_multiple_text_blocks(self, empty_db):
        db_path, conn = empty_db
        content = json.dumps([
            {"type": "text", "text": "first"},
            {"type": "text", "text": "second"},
        ])
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "assistant", content, "2026-03-20T10:00:00Z",
             0, 0, 0, 0, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        assert session.entries[0].text_content == "first\nsecond"

    def test_cache_tokens_in_assistant(self, empty_db):
        db_path, conn = empty_db
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("root1", "assistant", None, "2026-03-20T10:00:00Z",
             100, 50, 200, 300, None, None, None),
        )
        conn.commit()
        session = TapeReader(str(db_path)).read_session("root1")
        tok = session.entries[0].token_usage
        assert tok.cache_creation == 200
        assert tok.cache_read == 300
