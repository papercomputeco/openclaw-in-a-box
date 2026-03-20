"""Comprehensive tests for observer.py -- heuristic observation extractor."""

import json
import re
from pathlib import Path

import pytest

from tape_helpers import create_test_db, insert_node
from observer import (
    Observation,
    Observer,
    observe_session_inline,
    _first_user_message,
    _has_traceback,
    _extract_traceback_summary,
    _IMPORTANT_KEYWORDS,
    _POSSIBLE_KEYWORDS,
)
from tape_reader import TapeReader, TapeSession, TapeEntry, ToolUse, ToolResult, TokenUsage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_observer(tmp_path: Path, db_path: Path) -> Observer:
    memory_dir = tmp_path / "memory"
    return Observer(str(db_path), str(memory_dir))


def simple_session_db(db_path: Path) -> str:
    """Create a minimal single-session DB and return the root hash."""
    conn = create_test_db(db_path)
    insert_node(conn, hash="root1", role="user", text="Hello, do something useful",
                created_at="2026-03-20T10:00:00Z")
    insert_node(conn, hash="asst1", role="assistant", text="Sure, I will help.",
                parent_hash="root1", created_at="2026-03-20T10:01:00Z",
                prompt_tokens=100, completion_tokens=50)
    conn.close()
    return "root1"


# ---------------------------------------------------------------------------
# Observation dataclass tests
# ---------------------------------------------------------------------------

class TestObservationDataclass:
    def test_defaults(self):
        obs = Observation()
        assert obs.timestamp == ""
        assert obs.referenced_time == ""
        assert obs.priority == "informational"
        assert obs.content == ""
        assert obs.source_session == ""

    def test_construction_with_values(self):
        obs = Observation(
            timestamp="2026-03-20T10:00:00Z",
            referenced_time="2026-03-20T09:00:00Z",
            priority="important",
            content="Something happened",
            source_session="abc12345",
        )
        assert obs.timestamp == "2026-03-20T10:00:00Z"
        assert obs.priority == "important"
        assert obs.content == "Something happened"
        assert obs.source_session == "abc12345"


# ---------------------------------------------------------------------------
# Observer.run() tests
# ---------------------------------------------------------------------------

class TestObserverRun:
    def test_run_extracts_observations(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        simple_session_db(db_path)
        observer = make_observer(tmp_path, db_path)
        observations = observer.run()
        assert len(observations) >= 1
        contents = [o.content for o in observations]
        assert any("Session goal:" in c for c in contents)

    def test_run_writes_observations_md(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        simple_session_db(db_path)
        observer = make_observer(tmp_path, db_path)
        observer.run()
        md_path = tmp_path / "memory" / "observations.md"
        assert md_path.exists()
        content = md_path.read_text()
        assert "Session goal:" in content

    def test_run_saves_state(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        simple_session_db(db_path)
        observer = make_observer(tmp_path, db_path)
        observer.run()
        state_path = tmp_path / "memory" / "observer_state.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text())
        assert "processed_sessions" in state
        assert "root1" in state["processed_sessions"]

    def test_run_returns_empty_on_empty_db(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        observations = observer.run()
        assert observations == []

    def test_run_second_call_returns_empty_watermark(self, tmp_path):
        """Second run on same sessions should return no new observations."""
        db_path = tmp_path / "tapes.sqlite"
        simple_session_db(db_path)
        observer = make_observer(tmp_path, db_path)
        first_run = observer.run()
        assert len(first_run) > 0
        second_run = observer.run()
        assert second_run == []

    def test_run_no_file_written_when_no_observations(self, tmp_path):
        """If no sessions exist, observations.md should not be created."""
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        observer.run()
        md_path = tmp_path / "memory" / "observations.md"
        assert not md_path.exists()

    def test_run_multiple_sessions(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Task one",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="root2", role="user", text="Task two",
                    created_at="2026-03-20T11:00:00Z")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        observations = observer.run()
        contents = [o.content for o in observations]
        assert any("Task one" in c for c in contents)
        assert any("Task two" in c for c in contents)


# ---------------------------------------------------------------------------
# get_unprocessed_sessions() tests
# ---------------------------------------------------------------------------

class TestGetUnprocessedSessions:
    def test_returns_all_when_no_state(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="hello")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        unprocessed = observer.get_unprocessed_sessions()
        assert "root1" in unprocessed

    def test_excludes_already_processed(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="hello")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        # Pre-populate state with root1 as processed
        observer.save_state({"processed_sessions": ["root1"]})
        unprocessed = observer.get_unprocessed_sessions()
        assert "root1" not in unprocessed

    def test_empty_db_returns_empty(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        assert observer.get_unprocessed_sessions() == []


# ---------------------------------------------------------------------------
# observe_session() -- session goal extraction
# ---------------------------------------------------------------------------

class TestObserveSessionGoal:
    def test_extracts_first_user_message_as_goal(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user",
                    text="Build a recommendation engine",
                    created_at="2026-03-20T10:00:00Z")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        goals = [o for o in obs if "Session goal:" in o.content]
        assert len(goals) == 1
        assert "Build a recommendation engine" in goals[0].content

    def test_goal_truncated_to_300_chars(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        long_msg = "x" * 400
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text=long_msg,
                    created_at="2026-03-20T10:00:00Z")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        goals = [o for o in obs if "Session goal:" in o.content]
        assert len(goals) == 1
        # "Session goal: " is 14 chars, content must not exceed 314 total
        assert len(goals[0].content) <= 314

    def test_no_goal_when_no_user_message(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="assistant", text="Starting up",
                    created_at="2026-03-20T10:00:00Z", prompt_tokens=10,
                    completion_tokens=5)
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        goals = [o for o in obs if "Session goal:" in o.content]
        assert len(goals) == 0

    def test_system_reminder_skipped_as_goal(self, tmp_path):
        """system-reminder user nodes should be skipped; real goal used instead."""
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user",
                    text="<system-reminder>Some system noise</system-reminder>",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="node2", role="user",
                    text="Actual user goal here",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        goals = [o for o in obs if "Session goal:" in o.content]
        assert len(goals) == 1
        assert "Actual user goal here" in goals[0].content
        assert "system-reminder" not in goals[0].content

    def test_goal_source_session_set(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Do something",
                    created_at="2026-03-20T10:00:00Z")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        goals = [o for o in obs if "Session goal:" in o.content]
        assert goals[0].source_session == "root1"

    def test_goal_priority_is_informational(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Simple task",
                    created_at="2026-03-20T10:00:00Z")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        goals = [o for o in obs if "Session goal:" in o.content]
        assert goals[0].priority == "informational"


# ---------------------------------------------------------------------------
# observe_session() -- file creation detection
# ---------------------------------------------------------------------------

class TestObserveSessionFileCreation:
    def test_write_tool_creates_observation(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Create a file",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text="Writing the file now.",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=50, completion_tokens=20,
                    tool_uses=[{"name": "Write", "id": "tu1",
                                "input": {"file_path": "/tmp/foo.py"}}])
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        file_obs = [o for o in obs if "File created:" in o.content]
        assert len(file_obs) == 1
        assert "/tmp/foo.py" in file_obs[0].content

    def test_write_tool_priority_is_possible(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Create a file",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text="Writing now.",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=50, completion_tokens=20,
                    tool_uses=[{"name": "Write", "id": "tu1",
                                "input": {"file_path": "/tmp/bar.py"}}])
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        file_obs = [o for o in obs if "File created:" in o.content]
        assert file_obs[0].priority == "possible"

    def test_read_tool_does_not_create_file_observation(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Read a file",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text="Reading...",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=50, completion_tokens=20,
                    tool_uses=[{"name": "Read", "id": "tu1",
                                "input": {"file_path": "/tmp/existing.py"}}])
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        file_obs = [o for o in obs if "File created:" in o.content]
        assert len(file_obs) == 0


# ---------------------------------------------------------------------------
# observe_session() -- token usage extraction
# ---------------------------------------------------------------------------

class TestObserveSessionTokenUsage:
    def test_token_usage_extracted(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Do something",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant", text="Done.",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=200, completion_tokens=80)
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        token_obs = [o for o in obs if "Token usage:" in o.content]
        assert len(token_obs) == 1
        assert "200 input" in token_obs[0].content
        assert "80 output" in token_obs[0].content

    def test_no_token_usage_when_zero_tokens(self, tmp_path):
        """Sessions with zero input tokens should produce no token usage observation."""
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Hello",
                    created_at="2026-03-20T10:00:00Z")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        token_obs = [o for o in obs if "Token usage:" in o.content]
        assert len(token_obs) == 0

    def test_token_usage_sums_multiple_entries(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="First turn",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant", text="First response",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=100, completion_tokens=40)
        insert_node(conn, hash="user2", role="user", text="Second turn",
                    parent_hash="asst1",
                    created_at="2026-03-20T10:02:00Z")
        insert_node(conn, hash="asst2", role="assistant", text="Second response",
                    parent_hash="user2",
                    created_at="2026-03-20T10:03:00Z",
                    prompt_tokens=150, completion_tokens=60)
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        token_obs = [o for o in obs if "Token usage:" in o.content]
        assert len(token_obs) == 1
        assert "250 input" in token_obs[0].content
        assert "100 output" in token_obs[0].content


# ---------------------------------------------------------------------------
# observe_session() -- error tool result detection
# ---------------------------------------------------------------------------

class TestObserveSessionErrorDetection:
    def test_is_error_tool_result_creates_important_observation(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Do something",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text="Trying...",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=50, completion_tokens=10,
                    tool_uses=[{"name": "Bash", "id": "tu1",
                                "input": {"command": "ls /nonexistent"}}])
        insert_node(conn, hash="user2", role="user",
                    text="",
                    parent_hash="asst1",
                    created_at="2026-03-20T10:02:00Z",
                    tool_results=[{
                        "tool_use_id": "tu1",
                        "content": "ls: /nonexistent: No such file or directory",
                        "is_error": True,
                    }])
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        error_obs = [o for o in obs if "Tool error:" in o.content]
        assert len(error_obs) == 1
        assert error_obs[0].priority == "important"
        assert "No such file" in error_obs[0].content

    def test_non_error_tool_result_not_flagged(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Run something",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text="Running...",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=50, completion_tokens=10,
                    tool_uses=[{"name": "Bash", "id": "tu1",
                                "input": {"command": "echo hello"}}])
        insert_node(conn, hash="user2", role="user",
                    text="",
                    parent_hash="asst1",
                    created_at="2026-03-20T10:02:00Z",
                    tool_results=[{
                        "tool_use_id": "tu1",
                        "content": "hello",
                        "is_error": False,
                    }])
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        error_obs = [o for o in obs if "Tool error:" in o.content]
        assert len(error_obs) == 0


# ---------------------------------------------------------------------------
# observe_session() -- traceback detection
# ---------------------------------------------------------------------------

class TestObserveSessionTracebackDetection:
    def test_traceback_in_assistant_message_flagged(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        traceback_text = (
            "I see the following error:\n"
            "Traceback (most recent call last):\n"
            "  File 'foo.py', line 10, in bar\n"
            "ValueError: invalid value\n"
        )
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Fix this",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text=traceback_text,
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=100, completion_tokens=50)
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        tb_obs = [o for o in obs if "Exception discussed:" in o.content]
        assert len(tb_obs) == 1
        assert tb_obs[0].priority == "important"

    def test_exception_line_at_line_start_flagged(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        text_with_exception = "Analysis:\nKeyError: 'missing_key'\nEnd."
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Debug",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text=text_with_exception,
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=50, completion_tokens=20)
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        tb_obs = [o for o in obs if "Exception discussed:" in o.content]
        assert len(tb_obs) == 1

    def test_no_traceback_when_none_present(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="Hello",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text="Everything looks fine.",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=50, completion_tokens=20)
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        tb_obs = [o for o in obs if "Exception discussed:" in o.content]
        assert len(tb_obs) == 0

    def test_inline_error_mention_not_flagged_as_traceback(self, tmp_path):
        """Mentions of 'error' mid-sentence should not trigger traceback detection."""
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="How do I handle errors?",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="asst1", role="assistant",
                    text="Error handling is important. I see the error pattern here.",
                    parent_hash="root1",
                    created_at="2026-03-20T10:01:00Z",
                    prompt_tokens=50, completion_tokens=20)
        conn.close()
        observer = make_observer(tmp_path, db_path)
        session = observer.reader.read_session("root1")
        obs = observer.observe_session(session)
        tb_obs = [o for o in obs if "Exception discussed:" in o.content]
        assert len(tb_obs) == 0


# ---------------------------------------------------------------------------
# write_observations() tests
# ---------------------------------------------------------------------------

class TestWriteObservations:
    def test_creates_file_with_correct_format(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        obs_list = [
            Observation(
                timestamp="2026-03-20T10:00:00Z",
                referenced_time="2026-03-20T09:00:00Z",
                priority="important",
                content="Something important happened",
                source_session="abc123456789",
            )
        ]
        observer.write_observations(obs_list)
        md = (tmp_path / "memory" / "observations.md").read_text()
        assert "## 2026-03-20" in md
        assert "[important] Something important happened" in md
        assert "(session: abc12345)" in md

    def test_appends_to_existing_file(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        obs1 = [
            Observation(
                timestamp="2026-03-20T10:00:00Z",
                referenced_time="2026-03-20T09:00:00Z",
                priority="informational",
                content="First observation",
                source_session="aaa1111122223333",
            )
        ]
        obs2 = [
            Observation(
                timestamp="2026-03-20T11:00:00Z",
                referenced_time="2026-03-20T10:00:00Z",
                priority="possible",
                content="Second observation",
                source_session="bbb4444455556666",
            )
        ]
        observer.write_observations(obs1)
        observer.write_observations(obs2)
        md = (tmp_path / "memory" / "observations.md").read_text()
        assert "First observation" in md
        assert "Second observation" in md

    def test_date_header_not_duplicated(self, tmp_path):
        """Writing two batches with the same date should only add the header once."""
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        obs1 = [
            Observation(
                timestamp="2026-03-20T10:00:00Z",
                referenced_time="2026-03-20T09:00:00Z",
                priority="informational",
                content="First obs",
                source_session="aaa1",
            )
        ]
        obs2 = [
            Observation(
                timestamp="2026-03-20T11:00:00Z",
                referenced_time="2026-03-20T08:00:00Z",
                priority="informational",
                content="Second obs",
                source_session="bbb2",
            )
        ]
        observer.write_observations(obs1)
        observer.write_observations(obs2)
        md = (tmp_path / "memory" / "observations.md").read_text()
        assert md.count("## 2026-03-20") == 1

    def test_unknown_date_when_no_referenced_time(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        obs_list = [
            Observation(
                timestamp="2026-03-20T10:00:00Z",
                referenced_time="",
                priority="informational",
                content="No date obs",
                source_session="xxx0",
            )
        ]
        observer.write_observations(obs_list)
        md = (tmp_path / "memory" / "observations.md").read_text()
        assert "## unknown" in md

    def test_creates_memory_dir_if_missing(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        memory_dir = tmp_path / "nested" / "memory"
        observer = Observer(str(db_path), str(memory_dir))
        obs_list = [
            Observation(
                timestamp="2026-03-20T10:00:00Z",
                referenced_time="2026-03-20T09:00:00Z",
                priority="informational",
                content="Test",
                source_session="zzz0",
            )
        ]
        observer.write_observations(obs_list)
        assert (memory_dir / "observations.md").exists()


# ---------------------------------------------------------------------------
# load_state() / save_state() round-trip
# ---------------------------------------------------------------------------

class TestLoadSaveState:
    def test_load_state_returns_empty_dict_when_no_file(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        state = observer.load_state()
        assert state == {}

    def test_save_then_load_round_trip(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        data = {"processed_sessions": ["abc", "def"], "version": 1}
        observer.save_state(data)
        loaded = observer.load_state()
        assert loaded == data

    def test_save_state_creates_json_file(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        observer.save_state({"processed_sessions": ["x1"]})
        state_path = tmp_path / "memory" / "observer_state.json"
        assert state_path.exists()
        raw = json.loads(state_path.read_text())
        assert raw["processed_sessions"] == ["x1"]

    def test_save_state_creates_memory_dir(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        memory_dir = tmp_path / "deep" / "memory"
        observer = Observer(str(db_path), str(memory_dir))
        observer.save_state({"test": True})
        assert (memory_dir / "observer_state.json").exists()


# ---------------------------------------------------------------------------
# classify_priority() tests
# ---------------------------------------------------------------------------

class TestClassifyPriority:
    def test_important_keywords(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        important_terms = ["fix", "bug", "error", "fail", "crash", "broken",
                           "revert", "hotfix", "security", "vulnerability"]
        for term in important_terms:
            result = observer.classify_priority(f"We need to {term} this")
            assert result == "important", f"Expected 'important' for term '{term}'"

    def test_possible_keywords(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        possible_terms = ["test", "refactor", "rename", "cleanup", "reorganize",
                          "migrate", "deprecate", "update"]
        for term in possible_terms:
            result = observer.classify_priority(f"We should {term} this")
            assert result == "possible", f"Expected 'possible' for term '{term}'"

    def test_no_keyword_returns_default(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        result = observer.classify_priority("Just a normal observation")
        assert result == "informational"

    def test_custom_default_returned(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        result = observer.classify_priority("No matching terms", default="possible")
        assert result == "possible"

    def test_important_overrides_possible(self, tmp_path):
        """Important keywords take precedence even if possible keywords also present."""
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        result = observer.classify_priority("test failed with an error")
        assert result == "important"

    def test_case_insensitive_important(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        assert observer.classify_priority("Found a BUG") == "important"
        assert observer.classify_priority("System CRASH detected") == "important"

    def test_case_insensitive_possible(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        assert observer.classify_priority("Need to REFACTOR this") == "possible"


# ---------------------------------------------------------------------------
# observe_session_inline() tests
# ---------------------------------------------------------------------------

class TestObserveSessionInline:
    def test_returns_list_of_dicts(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        simple_session_db(db_path)
        result = observe_session_inline(str(db_path))
        assert isinstance(result, list)
        for item in result:
            assert "priority" in item
            assert "content" in item

    def test_returns_empty_for_empty_db(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        result = observe_session_inline(str(db_path))
        assert result == []

    def test_uses_most_recent_session_when_no_session_id(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="First session task",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="root2", role="user", text="Second session task",
                    created_at="2026-03-20T11:00:00Z")
        conn.close()
        result = observe_session_inline(str(db_path))
        contents = [r["content"] for r in result]
        # Should use the last session (root2) since no session_id given
        assert any("Second session task" in c for c in contents)

    def test_specific_session_id(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="First specific task",
                    created_at="2026-03-20T10:00:00Z")
        insert_node(conn, hash="root2", role="user", text="Second other task",
                    created_at="2026-03-20T11:00:00Z")
        conn.close()
        result = observe_session_inline(str(db_path), session_id="root1")
        contents = [r["content"] for r in result]
        assert any("First specific task" in c for c in contents)
        assert not any("Second other task" in c for c in contents)

    def test_no_file_io(self, tmp_path):
        """observe_session_inline should not create any files."""
        db_path = tmp_path / "tapes.sqlite"
        simple_session_db(db_path)
        observe_session_inline(str(db_path))
        # Only the DB should exist; no memory dir
        files = list(tmp_path.iterdir())
        assert all(f.name == "tapes.sqlite" for f in files)


# ---------------------------------------------------------------------------
# _first_user_message() tests
# ---------------------------------------------------------------------------

class TestFirstUserMessage:
    def _make_session(self, entries: list[TapeEntry]) -> TapeSession:
        return TapeSession(session_id="test", entries=entries, start_time="", end_time="")

    def test_returns_first_user_text(self):
        entries = [
            TapeEntry(type="user", text_content="Hello world"),
            TapeEntry(type="assistant", text_content="Hi there"),
        ]
        result = _first_user_message(self._make_session(entries))
        assert result == "Hello world"

    def test_skips_system_reminder(self):
        entries = [
            TapeEntry(type="user",
                      text_content="<system-reminder>noise</system-reminder>"),
            TapeEntry(type="user", text_content="Real user message"),
        ]
        result = _first_user_message(self._make_session(entries))
        assert result == "Real user message"

    def test_returns_empty_when_no_user_entries(self):
        entries = [
            TapeEntry(type="assistant", text_content="Just an assistant"),
        ]
        result = _first_user_message(self._make_session(entries))
        assert result == ""

    def test_returns_empty_when_all_are_system_reminders(self):
        entries = [
            TapeEntry(type="user",
                      text_content="<system-reminder>first</system-reminder>"),
            TapeEntry(type="user",
                      text_content="<system-reminder>second</system-reminder>"),
        ]
        result = _first_user_message(self._make_session(entries))
        assert result == ""

    def test_skips_empty_user_text(self):
        entries = [
            TapeEntry(type="user", text_content=""),
            TapeEntry(type="user", text_content="Non-empty message"),
        ]
        result = _first_user_message(self._make_session(entries))
        assert result == "Non-empty message"

    def test_empty_session(self):
        result = _first_user_message(self._make_session([]))
        assert result == ""


# ---------------------------------------------------------------------------
# _has_traceback() tests
# ---------------------------------------------------------------------------

class TestHasTraceback:
    def test_detects_traceback_header(self):
        assert _has_traceback("Traceback (most recent call last):\n  File x.py") is True

    def test_detects_error_at_line_start(self):
        assert _has_traceback("ValueError: bad value") is True

    def test_detects_exception_at_line_start(self):
        assert _has_traceback("RuntimeException: something failed") is True

    def test_ignores_error_mid_sentence(self):
        assert _has_traceback("I see the error in the code") is False

    def test_ignores_error_discussion(self):
        assert _has_traceback("Error handling is a broad topic") is False

    def test_multiline_with_error_at_start_of_line(self):
        text = "Some explanation\nKeyError: 'key'\nMore text"
        assert _has_traceback(text) is True

    def test_empty_string(self):
        assert _has_traceback("") is False

    def test_detects_various_error_types(self):
        for etype in ["AttributeError:", "ImportError:", "TypeError:", "OSError:"]:
            assert _has_traceback(etype + " message") is True


# ---------------------------------------------------------------------------
# _extract_traceback_summary() tests
# ---------------------------------------------------------------------------

class TestExtractTracebackSummary:
    def test_extracts_last_error_line(self):
        text = (
            "Traceback (most recent call last):\n"
            "  File 'foo.py', line 1\n"
            "ValueError: bad input\n"
        )
        result = _extract_traceback_summary(text)
        assert "ValueError: bad input" in result

    def test_extracts_exception_line(self):
        text = "Some context\nRuntimeException: out of memory\nEnd"
        result = _extract_traceback_summary(text)
        assert "RuntimeException: out of memory" in result

    def test_truncates_to_200_chars(self):
        long_error = "ValueError: " + "x" * 300
        result = _extract_traceback_summary(long_error)
        assert len(result) <= 200

    def test_fallback_when_no_error_line(self):
        text = "Just some normal text without error lines"
        result = _extract_traceback_summary(text)
        assert result == text[:200]

    def test_prefers_last_error_line(self):
        text = "First error: ValueError: first\nSecond error: TypeError: second"
        result = _extract_traceback_summary(text)
        assert "TypeError: second" in result

    def test_empty_string_fallback(self):
        result = _extract_traceback_summary("")
        assert result == ""


# ---------------------------------------------------------------------------
# Edge cases and integration
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_observe_session_with_empty_session(self, tmp_path):
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        empty_session = TapeSession(session_id="empty", entries=[], start_time="", end_time="")
        obs = observer.observe_session(empty_session)
        assert obs == []

    def test_run_accumulates_new_sessions_in_state(self, tmp_path):
        """After run(), state should include sessions added after first run."""
        db_path = tmp_path / "tapes.sqlite"
        conn = create_test_db(db_path)
        insert_node(conn, hash="root1", role="user", text="First",
                    created_at="2026-03-20T10:00:00Z")
        conn.close()
        observer = make_observer(tmp_path, db_path)
        observer.run()

        # Add a new session
        conn = sqlite3.connect(str(db_path))
        from tape_helpers import insert_node as _ins
        _ins(conn, hash="root2", role="user", text="Second",
             created_at="2026-03-20T11:00:00Z")
        conn.close()

        obs2 = observer.run()
        contents = [o.content for o in obs2]
        assert any("Second" in c for c in contents)

        state = observer.load_state()
        assert "root1" in state["processed_sessions"]
        assert "root2" in state["processed_sessions"]

    def test_keyword_patterns_are_word_boundary(self, tmp_path):
        """Substrings like 'tester' should not match 'test' keyword."""
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)
        # 'tester' should not match 'test' keyword
        result = observer.classify_priority("I am a tester with a bugtracker")
        # 'bug' is a substring of 'bugtracker' — but regex uses \b so no match
        assert result == "informational"

    def test_write_tool_without_input_summary_not_observed(self, tmp_path):
        """A Write tool use with empty input_summary should not produce observation."""
        from tape_reader import TapeSession, TapeEntry, ToolUse, TokenUsage
        db_path = tmp_path / "tapes.sqlite"
        create_test_db(db_path).close()
        observer = make_observer(tmp_path, db_path)

        entry = TapeEntry(
            type="assistant",
            timestamp="2026-03-20T10:01:00Z",
            text_content="Writing...",
            tool_uses=[ToolUse(id="tu1", name="Write", input_summary="")],
            token_usage=TokenUsage(input_tokens=10, output_tokens=5),
        )
        session = TapeSession(
            session_id="sess1",
            entries=[entry],
            start_time="2026-03-20T10:01:00Z",
            end_time="2026-03-20T10:01:00Z",
        )
        obs = observer.observe_session(session)
        file_obs = [o for o in obs if "File created:" in o.content]
        assert len(file_obs) == 0


import sqlite3  # noqa: E402 -- needed for test_run_accumulates
