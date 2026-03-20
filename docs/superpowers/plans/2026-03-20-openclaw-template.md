# OpenClaw Template Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a minimal, working openclaw skill template in `claw-stereo` that proves out the stereos+tapes+jcard pattern from `../pokemon` and can be extracted as a project generator later.

**Architecture:** A skeleton "claw" agent that runs inside a stereos VM via masterblaster (`mb up`). The agent is a simple Python script that demonstrates the full integration surface: jcard.toml VM config, install.sh for NixOS setup, tapes telemetry, SKILL.md with openclaw metadata, and observational memory. The agent itself does something trivial (analyzes a repo and writes a summary) so the focus stays on the infrastructure pattern, not domain logic.

**Tech Stack:** Python 3.11+, stereos (NixOS VM), masterblaster (mb CLI), tapes (telemetry), pytest

---

## File Structure

```
claw-stereo/
├── jcard.toml                # stereos VM config (copied pattern from pokemon)
├── pyproject.toml             # Python project metadata + deps
├── SKILL.md                   # openclaw skill definition with metadata
├── README.md                  # How to use this template
├── .gitignore                 # Output dirs, tapes, venv
├── scripts/
│   ├── install.sh             # NixOS/macOS dep installer (tapes, python)
│   ├── agent.py               # Minimal agent loop (repo analyzer)
│   ├── tape_reader.py         # Tapes SQLite reader (stdlib only, ported from pokemon)
│   ├── observer.py            # Observation extractor (ported from pokemon)
│   └── observe_cli.py         # Observer CLI entry point
├── references/                # Domain-specific reference data (empty placeholder)
├── output/                    # Agent output directory (gitignored)
├── .tapes/                    # Tapes DB + config (gitignored)
│   └── memory/                # Observational memory
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── tape_helpers.py        # Shared test DB fixtures (real Tapes schema)
    ├── test_agent.py
    ├── test_tape_reader.py
    └── test_observer.py
```

**Design decisions:**
- `scripts/` mirrors the pokemon layout so templates feel familiar
- `tape_reader.py` and `observer.py` are ported from pokemon with the real Tapes schema (11 columns: `hash, role, content, created_at, prompt_tokens, completion_tokens, cache_creation_input_tokens, cache_read_input_tokens, parent_hash, model, agent_name`). Content is JSON blobs parsed via `_parse_content_blob`
- `tests/tape_helpers.py` extracts shared DB creation to avoid duplicating schema across test files
- `agent.py` is intentionally trivial (reads files, writes a summary) to keep focus on the template pattern
- `references/` is an empty directory placeholder showing where domain data goes
- `output/` replaces pokemon's `frames/` + `pokedex/` with a generic output dir

---

### Task 1: Initialize Git Repository and Project Skeleton

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `references/.gitkeep`
- Create: `tests/__init__.py`

- [ ] **Step 1: Initialize git repo**

Run: `cd /Users/bdougie/code/papercomputeco/claw-stereo && git init`
Expected: `Initialized empty Git repository`

- [ ] **Step 2: Create .gitignore**

```gitignore
# Runtime output
output/*
!output/.gitkeep

# Tapes telemetry
.tapes/

# Python
__pycache__/
*.pyc
*.egg-info/
venv/
.venv/

# OS
.DS_Store

# ROM / data files users bring
rom/
data/
```

Note: `output/*` with `!output/.gitkeep` allows tracking the gitkeep while ignoring output contents.

- [ ] **Step 3: Create pyproject.toml**

```toml
[project]
name = "claw-stereo"
version = "0.1.0"
description = "OpenClaw skill template for stereOS agents"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = [
    "pytest",
    "pytest-cov",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["scripts", "tests"]

[tool.coverage.run]
source = ["scripts"]
omit = ["scripts/observe_cli.py"]

[tool.coverage.report]
show_missing = true
fail_under = 100
```

- [ ] **Step 4: Create placeholder files**

Create `references/.gitkeep` (empty), `output/.gitkeep` (empty), `tests/__init__.py` (empty).

- [ ] **Step 5: Commit**

```bash
git add .gitignore pyproject.toml references/.gitkeep output/.gitkeep tests/__init__.py
git commit -m "chore: initialize project skeleton with pyproject.toml and gitignore"
```

---

### Task 2: Create jcard.toml (stereos VM Configuration)

**Files:**
- Create: `jcard.toml`

**Reference:** `/Users/bdougie/code/papercomputeco/pokemon/jcard.toml`

- [ ] **Step 1: Write jcard.toml**

```toml
# jcard.toml — stereOS VM configuration for OpenClaw skill template

mixtape = "opencode-mixtape:latest"

name = "claw-stereo"

[resources]
cpus   = 2
memory = "4GiB"
disk   = "20GiB"

[network]
mode = "nat"

# Uncomment for LLM-powered agent:
# egress_allow = ["api.anthropic.com"]

[[shared]]
host = "./"
guest = "/workspace"
readonly = false

[secrets]
# Inject API keys from host environment:
# ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"

[agent]
harness = "claude-code"
prompt = "cd /workspace && bash scripts/install.sh && export LD_LIBRARY_PATH=$HOME/.nix-profile/lib:$LD_LIBRARY_PATH && export PATH=/usr/local/bin:$PATH && tapes serve proxy --config-dir /workspace/.tapes --sqlite /workspace/.tapes/tapes.sqlite & sleep 2 && ~/venv/bin/python3 scripts/agent.py /workspace"
workdir = "/workspace"
restart = "no"
```

- [ ] **Step 2: Commit**

```bash
git add jcard.toml
git commit -m "feat: add jcard.toml stereos VM configuration"
```

---

### Task 3: Create install.sh (NixOS/macOS Setup Script)

**Files:**
- Create: `scripts/install.sh`

**Reference:** `/Users/bdougie/code/papercomputeco/pokemon/scripts/install.sh`

Simplified from pokemon -- no PyBoy/numpy/Pillow since this template has no domain-specific native deps. Keeps NixOS detection, DNS fix, venv creation, tapes installation, and permission fixes.

- [ ] **Step 1: Write install.sh**

```bash
#!/usr/bin/env bash
# Install dependencies for the OpenClaw skill.
# Works on macOS, Linux, and inside stereOS VMs (NixOS).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== OpenClaw Skill Setup ==="
echo "Skill directory: $SKILL_DIR"

# ---------------------------------------------------------------------------
# Detect NixOS (stereOS VMs use NixOS)
# ---------------------------------------------------------------------------
IS_NIXOS=false
if [ -f /etc/NIXOS ] || [ -d /nix/store ]; then
    IS_NIXOS=true
    echo "Detected NixOS environment"
fi

# ---------------------------------------------------------------------------
# Fix DNS inside stereOS VMs (systemd-resolved stub often broken)
# ---------------------------------------------------------------------------
if $IS_NIXOS; then
    if ! nslookup google.com &>/dev/null 2>&1; then
        echo "Fixing DNS (systemd-resolved not forwarding)..."
        sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'
    fi
fi

# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    if $IS_NIXOS; then
        echo "Installing Python via nix..."
        nix profile install nixpkgs#python312
    else
        echo "ERROR: python3 not found. Install Python 3.10+ first."
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# ---------------------------------------------------------------------------
# Python venv (NixOS needs this to avoid writing to /nix/store)
# ---------------------------------------------------------------------------
if $IS_NIXOS; then
    if [ ! -d "$HOME/venv" ]; then
        echo "Creating Python venv..."
        python3 -m venv "$HOME/venv"
    fi
    # Install any pip dependencies here:
    # "$HOME/venv/bin/pip" install --quiet <your-deps>
else
    echo "Local environment -- using system Python"
fi

# ---------------------------------------------------------------------------
# Writable directories (shared mount permissions)
# ---------------------------------------------------------------------------
for dir in output .tapes; do
    mkdir -p "$SKILL_DIR/$dir"
    chmod a+rwx "$SKILL_DIR/$dir" 2>/dev/null || true
done

# ---------------------------------------------------------------------------
# Tapes CLI
# ---------------------------------------------------------------------------
if ! command -v tapes &>/dev/null && [ ! -f /usr/local/bin/tapes ]; then
    echo ""
    echo "Installing Tapes CLI..."
    sudo mkdir -p /usr/local/bin
    curl -fsSL https://download.tapes.dev/install | bash

    # NixOS: patch the dynamically linked binary for the nix linker
    if $IS_NIXOS && [ -f /usr/local/bin/tapes ]; then
        INTERP=$(find /nix/store -name "ld-linux-*.so.1" 2>/dev/null | head -1)
        if [ -n "$INTERP" ]; then
            if ! command -v patchelf &>/dev/null; then
                nix profile install nixpkgs#patchelf
            fi
            echo "Patching tapes binary for NixOS..."
            patchelf --set-interpreter "$INTERP" /usr/local/bin/tapes
        fi
    fi
fi

# Verify tapes
if command -v tapes &>/dev/null; then
    tapes version
elif [ -f /usr/local/bin/tapes ]; then
    /usr/local/bin/tapes version
fi

# Initialize Tapes in the project if not already done
if [ ! -f "$SKILL_DIR/.tapes/config.toml" ]; then
    echo "Initializing Tapes..."
    mkdir -p "$SKILL_DIR/.tapes"
    cd "$SKILL_DIR" && tapes init --preset anthropic 2>/dev/null \
        || /usr/local/bin/tapes init --preset anthropic
fi

echo ""
echo "=== Setup complete ==="
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/install.sh`

- [ ] **Step 3: Commit**

```bash
git add scripts/install.sh
git commit -m "feat: add install.sh for NixOS/macOS dependency setup"
```

---

### Task 4: Create tape_reader.py and Shared Test Helpers

**Files:**
- Create: `scripts/tape_reader.py`
- Create: `tests/conftest.py`
- Create: `tests/tape_helpers.py`
- Create: `tests/test_tape_reader.py`

**Reference:** `/Users/bdougie/code/papercomputeco/pokemon/scripts/tape_reader.py`

Port from pokemon. Uses the real Tapes schema (11 columns). Content is JSON blobs parsed into structured `TapeEntry` objects with `text_content`, `tool_uses`, `tool_results`, and `token_usage` fields.

- [ ] **Step 1: Read the pokemon tape_reader.py for the full implementation**

Read: `/Users/bdougie/code/papercomputeco/pokemon/scripts/tape_reader.py`

- [ ] **Step 2: Write tests/tape_helpers.py (shared test DB factory)**

```python
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
```

- [ ] **Step 3: Write tests/conftest.py**

```python
"""Shared test fixtures."""
```

- [ ] **Step 4: Write the failing test for tape_reader**

```python
# tests/test_tape_reader.py
"""Tests for tape_reader -- Tapes SQLite reader."""
import pytest
from tape_helpers import create_test_db, insert_node
from tape_reader import TapeReader, TapeEntry, TapeSession


@pytest.fixture
def tape_db(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="root1", role="user", text="Hello world",
                created_at="2026-03-20T10:00:00Z")
    insert_node(conn, hash="reply1", role="assistant", text="Hi there!",
                parent_hash="root1", model="claude-3",
                created_at="2026-03-20T10:00:01Z",
                prompt_tokens=10, completion_tokens=20)
    return db_path


def test_tape_entry_defaults():
    entry = TapeEntry()
    assert entry.type == ""
    assert entry.text_content == ""
    assert entry.token_usage.input_tokens == 0


def test_list_sessions(tape_db):
    reader = TapeReader(str(tape_db))
    sessions = reader.list_sessions()
    assert sessions == ["root1"]


def test_read_session(tape_db):
    reader = TapeReader(str(tape_db))
    session = reader.read_session("root1")
    assert isinstance(session, TapeSession)
    assert len(session.entries) == 2
    assert session.entries[0].type == "user"
    assert session.entries[0].text_content == "Hello world"
    assert session.entries[1].type == "assistant"
    assert session.entries[1].text_content == "Hi there!"
    assert session.entries[1].token_usage.input_tokens == 10
    assert session.entries[1].token_usage.output_tokens == 20


def test_iter_entries(tape_db):
    reader = TapeReader(str(tape_db))
    entries = list(reader.iter_entries("root1"))
    assert len(entries) == 2


def test_read_session_with_tool_use(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user", text="Read file")
    insert_node(conn, hash="a1", role="assistant", parent_hash="r1",
                tool_uses=[{"id": "tu1", "name": "Read", "input": {"file_path": "/tmp/test.py"}}])
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert len(session.entries[1].tool_uses) == 1
    assert session.entries[1].tool_uses[0].name == "Read"
    assert session.entries[1].tool_uses[0].input_summary == "/tmp/test.py"


def test_read_session_with_tool_result(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user", text="Check this",
                tool_results=[{"tool_use_id": "tu1", "content": "file contents", "is_error": False}])
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert len(session.entries[0].tool_results) == 1
    assert session.entries[0].tool_results[0].content_summary == "file contents"


def test_read_session_with_error_tool_result(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user",
                tool_results=[{"tool_use_id": "tu1", "content": "not found", "is_error": True}])
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert session.entries[0].tool_results[0].is_error is True


def test_parse_none_content(tmp_path):
    """Nodes with NULL content should produce empty text_content."""
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    conn.execute(
        "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("r1", "user", None, "2026-03-20T10:00:00Z", 0, 0, 0, 0, None, None, None),
    )
    conn.commit()
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert session.entries[0].text_content == ""


def test_parse_invalid_json_content(tmp_path):
    """Nodes with malformed JSON should produce empty text_content."""
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    conn.execute(
        "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("r1", "user", "not json at all", "2026-03-20T10:00:00Z", 0, 0, 0, 0, None, None, None),
    )
    conn.commit()
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert session.entries[0].text_content == ""


def test_empty_session(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    create_test_db(db_path)
    reader = TapeReader(str(db_path))
    session = reader.read_session("nonexistent")
    assert session.entries == []


def test_summarize_tool_input_bash(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user", text="run it")
    insert_node(conn, hash="a1", role="assistant", parent_hash="r1",
                tool_uses=[{"id": "tu1", "name": "Bash", "input": {"command": "ls -la"}}])
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert session.entries[1].tool_uses[0].input_summary == "ls -la"


def test_summarize_tool_input_grep(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user", text="search")
    insert_node(conn, hash="a1", role="assistant", parent_hash="r1",
                tool_uses=[{"id": "tu1", "name": "Grep", "input": {"pattern": "TODO"}}])
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert "TODO" in session.entries[1].tool_uses[0].input_summary


def test_summarize_tool_input_unknown(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user", text="do thing")
    insert_node(conn, hash="a1", role="assistant", parent_hash="r1",
                tool_uses=[{"id": "tu1", "name": "CustomTool", "input": {"query": "test query"}}])
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert "test query" in session.entries[1].tool_uses[0].input_summary


def test_summarize_tool_input_fallback(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user", text="do thing")
    insert_node(conn, hash="a1", role="assistant", parent_hash="r1",
                tool_uses=[{"id": "tu1", "name": "CustomTool", "input": {"unusual_key": "val"}}])
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert session.entries[1].tool_uses[0].input_summary != ""


def test_tool_result_list_content(tmp_path):
    """Tool results with list content should be joined."""
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    import json
    content = json.dumps([{"type": "tool_result", "tool_use_id": "tu1",
                           "content": [{"type": "text", "text": "line1"}, {"type": "text", "text": "line2"}]}])
    conn.execute(
        "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("r1", "user", content, "2026-03-20T10:00:00Z", 0, 0, 0, 0, None, None, None),
    )
    conn.commit()
    reader = TapeReader(str(db_path))
    session = reader.read_session("r1")
    assert "line1" in session.entries[0].tool_results[0].content_summary


def test_non_dict_tool_input(tmp_path):
    """Non-dict tool_input should be stringified."""
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    import json
    content = json.dumps([{"type": "tool_use", "tool_use_id": "tu1",
                           "tool_name": "Test", "tool_input": "raw string"}])
    conn.execute(
        "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("a1", "assistant", content, "2026-03-20T10:00:00Z", 0, 0, 0, 0, None, None, None),
    )
    conn.commit()
    reader = TapeReader(str(db_path))
    session = reader.read_session("a1")
    assert session.entries[0].tool_uses[0].input_summary == "raw string"
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd /Users/bdougie/code/papercomputeco/claw-stereo && python3 -m pytest tests/test_tape_reader.py -v`
Expected: FAIL -- `ModuleNotFoundError: No module named 'tape_reader'`

- [ ] **Step 6: Write tape_reader.py (ported from pokemon)**

Port the full `tape_reader.py` from `/Users/bdougie/code/papercomputeco/pokemon/scripts/tape_reader.py`. Copy it verbatim -- it's stdlib-only and designed to be reusable. The key elements:
- `TapeEntry` dataclass with `text_content`, `tool_uses`, `tool_results`, `token_usage`
- `TapeSession` dataclass wrapping a list of entries
- `TapeReader` class with `list_sessions()`, `read_session()`, `iter_entries()`
- `_parse_content_blob()` to handle JSON content column
- `_summarize_tool_input()` for tool use summaries
- Recursive CTE query using real column names: `prompt_tokens`, `completion_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `parent_hash`, `model`, `agent_name`

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_tape_reader.py -v`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add scripts/tape_reader.py tests/tape_helpers.py tests/conftest.py tests/__init__.py tests/test_tape_reader.py
git commit -m "feat: add tape_reader.py -- stdlib-only Tapes SQLite reader"
```

---

### Task 5: Create observer.py (Observation Extractor)

**Files:**
- Create: `scripts/observer.py`
- Create: `tests/test_observer.py`

**Reference:** `/Users/bdougie/code/papercomputeco/pokemon/scripts/observer.py`

Port from pokemon. Uses `TapeReader.read_session()` which returns `TapeSession` objects with structured `TapeEntry` fields. Keyword matching operates on `text_content` (already parsed from JSON), not raw content blobs.

- [ ] **Step 1: Read the pokemon observer.py for the full implementation**

Read: `/Users/bdougie/code/papercomputeco/pokemon/scripts/observer.py`

- [ ] **Step 2: Write the failing test**

```python
# tests/test_observer.py
"""Tests for observer -- heuristic observation extractor."""
import json
from pathlib import Path

import pytest
from tape_helpers import create_test_db, insert_node
from observer import Observer, Observation, observe_session_inline


@pytest.fixture
def tape_db(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="root1", role="user",
                text="Fix the bug in auth module",
                created_at="2026-03-20T10:00:00Z")
    insert_node(conn, hash="reply1", role="assistant",
                text="Found error in login handler. Created auth_fix.py",
                parent_hash="root1", model="claude-3",
                created_at="2026-03-20T10:00:01Z",
                prompt_tokens=100, completion_tokens=200,
                tool_uses=[{"id": "tu1", "name": "Write", "input": {"file_path": "auth_fix.py"}}])
    return db_path


@pytest.fixture
def memory_dir(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    return d


def test_observation_defaults():
    obs = Observation()
    assert obs.priority == "informational"
    assert obs.content == ""


def test_observer_run(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    observations = obs.run()
    assert len(observations) > 0
    priorities = [o.priority for o in observations]
    # "error" and "bug" in content should trigger "important"
    assert "important" in priorities


def test_observer_session_goal(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    observations = obs.run()
    goals = [o for o in observations if "Session goal" in o.content]
    assert len(goals) == 1
    assert "Fix the bug" in goals[0].content


def test_observer_file_created(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    observations = obs.run()
    files = [o for o in observations if "File created" in o.content]
    assert len(files) == 1
    assert "auth_fix.py" in files[0].content


def test_observer_token_usage(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    observations = obs.run()
    tokens = [o for o in observations if "Token usage" in o.content]
    assert len(tokens) == 1
    assert "100" in tokens[0].content


def test_observer_writes_markdown(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    obs.run()
    md_file = memory_dir / "observations.md"
    assert md_file.exists()
    content = md_file.read_text()
    assert "[important]" in content


def test_observer_watermark(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    obs.run()
    # Second run should find no new sessions
    observations2 = obs.run()
    assert len(observations2) == 0


def test_observer_empty_db(tmp_path):
    db_path = tmp_path / "empty.sqlite"
    create_test_db(db_path)
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    obs = Observer(str(db_path), str(memory_dir))
    assert obs.run() == []


def test_observer_error_tool_result(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user", text="Run tests")
    insert_node(conn, hash="u1", role="user", parent_hash="r1",
                tool_results=[{"tool_use_id": "tu1", "content": "FAILED: assert 1==2", "is_error": True}])
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    obs = Observer(str(db_path), str(memory_dir))
    observations = obs.run()
    errors = [o for o in observations if "Tool error" in o.content]
    assert len(errors) == 1


def test_observer_traceback_detection(tmp_path):
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user", text="Check logs")
    insert_node(conn, hash="a1", role="assistant", parent_hash="r1",
                text="Traceback (most recent call last):\n  File 'x.py'\nValueError: bad input",
                prompt_tokens=10, completion_tokens=20)
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    obs = Observer(str(db_path), str(memory_dir))
    observations = obs.run()
    tracebacks = [o for o in observations if "Exception discussed" in o.content]
    assert len(tracebacks) == 1


def test_classify_priority_important(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    assert obs.classify_priority("found a critical bug") == "important"
    assert obs.classify_priority("security vulnerability") == "important"


def test_classify_priority_possible(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    assert obs.classify_priority("refactor the auth module") == "possible"
    assert obs.classify_priority("added test for login") == "possible"


def test_classify_priority_informational(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    assert obs.classify_priority("updated documentation") == "possible"
    assert obs.classify_priority("general notes") == "informational"


def test_observe_session_inline(tape_db):
    results = observe_session_inline(str(tape_db))
    assert len(results) > 0
    assert all("priority" in r and "content" in r for r in results)


def test_observe_session_inline_empty(tmp_path):
    db_path = tmp_path / "empty.sqlite"
    create_test_db(db_path)
    assert observe_session_inline(str(db_path)) == []


def test_observe_session_inline_specific(tape_db):
    results = observe_session_inline(str(tape_db), session_id="root1")
    assert len(results) > 0


def test_system_reminder_skipped(tmp_path):
    """System reminder messages should not appear as session goals."""
    db_path = tmp_path / "tapes.sqlite"
    conn = create_test_db(db_path)
    insert_node(conn, hash="r1", role="user",
                text="<system-reminder>internal noise</system-reminder>")
    insert_node(conn, hash="r2", role="user", parent_hash="r1",
                text="Actual user request")
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    obs = Observer(str(db_path), str(memory_dir))
    observations = obs.run()
    goals = [o for o in observations if "Session goal" in o.content]
    assert len(goals) == 1
    assert "Actual user request" in goals[0].content


def test_load_save_state(tape_db, memory_dir):
    obs = Observer(str(tape_db), str(memory_dir))
    assert obs.load_state() == {}
    obs.save_state({"processed_sessions": ["abc"]})
    state = obs.load_state()
    assert state["processed_sessions"] == ["abc"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_observer.py -v`
Expected: FAIL -- `ModuleNotFoundError: No module named 'observer'`

- [ ] **Step 4: Write observer.py (ported from pokemon)**

Port the full `observer.py` from `/Users/bdougie/code/papercomputeco/pokemon/scripts/observer.py`. Copy it verbatim -- it uses `TapeReader.read_session()` which returns `TapeSession` objects. Key elements:
- `Observation` dataclass with `timestamp`, `referenced_time`, `priority`, `content`, `source_session`
- `Observer` class with `run()`, `get_unprocessed_sessions()`, `observe_session()`, `classify_priority()`, `write_observations()`, `load_state()`, `save_state()`
- `observe_session_inline()` standalone function for programmatic use
- `_first_user_message()` that skips `<system-reminder>` noise
- `_has_traceback()` and `_extract_traceback_summary()` helpers
- Keyword regex patterns for priority classification

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_observer.py -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add scripts/observer.py tests/test_observer.py
git commit -m "feat: add observer.py -- heuristic observation extractor from Tapes"
```

---

### Task 6: Create observe_cli.py (Observer CLI Entry Point)

**Files:**
- Create: `scripts/observe_cli.py`

Thin CLI wrapper around `Observer`. Not coverage-tracked (omitted in pyproject.toml).

- [ ] **Step 1: Write observe_cli.py**

```python
#!/usr/bin/env python3
"""CLI for running the observation extractor.

Usage:
    python3 scripts/observe_cli.py [--db PATH] [--dry-run] [--reset]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from observer import Observer


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract observations from Tapes sessions")
    parser.add_argument("--db", default=".tapes/tapes.sqlite", help="Path to tapes.sqlite")
    parser.add_argument("--memory-dir", default=".tapes/memory", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--reset", action="store_true", help="Reprocess all sessions")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Tapes database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    memory_dir = Path(args.memory_dir)
    memory_dir.mkdir(parents=True, exist_ok=True)

    if args.reset:
        state_file = memory_dir / "observer_state.json"
        if state_file.exists():
            state_file.unlink()
            print("Reset watermark -- will reprocess all sessions")

    obs = Observer(str(db_path), str(memory_dir))

    if args.dry_run:
        sessions = obs.get_unprocessed_sessions()
        for sid in sessions:
            session = obs.reader.read_session(sid)
            observations = obs.observe_session(session)
            for o in observations:
                print(f"  [{o.priority}] {o.content[:80]}")
        print(f"\nDry run: {len(sessions)} sessions, would extract observations")
    else:
        observations = obs.run()
        if not observations:
            print("No new observations found.")
        else:
            for o in observations:
                print(f"  [{o.priority}] {o.content[:80]}")
            print(f"\nWrote {len(observations)} observations to {memory_dir / 'observations.md'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/observe_cli.py`

- [ ] **Step 3: Commit**

```bash
git add scripts/observe_cli.py
git commit -m "feat: add observe_cli.py -- CLI for running the observer"
```

---

### Task 7: Create agent.py (Minimal Agent Loop)

**Files:**
- Create: `scripts/agent.py`
- Create: `tests/test_agent.py`

The agent is intentionally simple: walks a directory, counts files, and writes a summary to `output/summary.md`. Demonstrates the agent loop pattern (read state, decide, act, log) without domain complexity.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent.py
"""Tests for agent -- minimal repo analyzer agent."""
from pathlib import Path
from unittest.mock import patch

import pytest

from agent import analyze_directory, write_summary, main


@pytest.fixture
def sample_dir(tmp_path):
    (tmp_path / "hello.py").write_text("print('hello')\n")
    (tmp_path / "README.md").write_text("# Test Project\n\nA test.\n")
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "lib.py").write_text("def add(a, b):\n    return a + b\n")
    return tmp_path


def test_analyze_directory(sample_dir):
    result = analyze_directory(str(sample_dir))
    assert result["total_files"] == 3
    assert ".py" in result["extensions"]
    assert ".md" in result["extensions"]
    assert result["total_lines"] > 0


def test_analyze_empty_directory(tmp_path):
    result = analyze_directory(str(tmp_path))
    assert result["total_files"] == 0
    assert result["extensions"] == {}
    assert result["total_lines"] == 0


def test_write_summary(tmp_path, sample_dir):
    result = analyze_directory(str(sample_dir))
    output_path = tmp_path / "summary.md"
    write_summary(result, str(output_path))
    assert output_path.exists()
    content = output_path.read_text()
    assert "3" in content
    assert ".py" in content


def test_write_summary_creates_parent_dirs(tmp_path, sample_dir):
    result = analyze_directory(str(sample_dir))
    output_path = tmp_path / "nested" / "dir" / "summary.md"
    write_summary(result, str(output_path))
    assert output_path.exists()


def test_main_writes_output(sample_dir, tmp_path):
    output_file = tmp_path / "summary.md"
    with patch("sys.argv", ["agent.py", str(sample_dir), "--output", str(output_file)]):
        main()
    assert output_file.exists()


def test_main_invalid_directory(tmp_path, capsys):
    with patch("sys.argv", ["agent.py", str(tmp_path / "nonexistent")]):
        with pytest.raises(SystemExit):
            main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_agent.py -v`
Expected: FAIL -- `ModuleNotFoundError: No module named 'agent'`

- [ ] **Step 3: Write agent.py implementation**

```python
#!/usr/bin/env python3
"""Minimal agent that analyzes a directory and writes a summary.

This is a template agent -- replace the logic in analyze_directory()
and write_summary() with your domain-specific agent behavior.

Usage:
    python3 scripts/agent.py /path/to/dir [--output output/summary.md]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path


def analyze_directory(directory: str) -> dict:
    """Walk a directory and collect file statistics.

    Returns a dict with total_files, total_lines, and extension counts.
    Replace this with your domain-specific state reading.
    """
    extensions: Counter[str] = Counter()
    total_files = 0
    total_lines = 0

    for root, _dirs, files in os.walk(directory):
        for fname in files:
            fpath = Path(root) / fname
            ext = fpath.suffix or "(no ext)"
            extensions[ext] += 1
            total_files += 1
            try:
                total_lines += len(fpath.read_text(errors="replace").splitlines())
            except (OSError, UnicodeDecodeError):
                pass

    return {
        "directory": directory,
        "total_files": total_files,
        "total_lines": total_lines,
        "extensions": dict(extensions),
    }


def write_summary(result: dict, output_path: str) -> None:
    """Write analysis results to a markdown file.

    Replace this with your domain-specific output logic.
    """
    lines = [
        "# Directory Analysis",
        "",
        f"**Directory:** `{result['directory']}`",
        f"**Total files:** {result['total_files']}",
        f"**Total lines:** {result['total_lines']}",
        "",
        "## File Types",
        "",
    ]
    for ext, count in sorted(result["extensions"].items(), key=lambda x: -x[1]):
        lines.append(f"- `{ext}`: {count} files")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a directory")
    parser.add_argument("directory", help="Directory to analyze")
    parser.add_argument("--output", default="output/summary.md", help="Output file path")
    args = parser.parse_args()

    if not Path(args.directory).is_dir():
        print(f"Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing: {args.directory}")
    result = analyze_directory(args.directory)
    print(f"Found {result['total_files']} files, {result['total_lines']} lines")

    write_summary(result, args.output)
    print(f"Summary written to: {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_agent.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add scripts/agent.py tests/test_agent.py
git commit -m "feat: add agent.py -- minimal directory analyzer agent"
```

---

### Task 8: Create SKILL.md (OpenClaw Skill Definition)

**Files:**
- Create: `SKILL.md`

**Reference:** `/Users/bdougie/code/papercomputeco/pokemon/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

The SKILL.md should contain:
- YAML frontmatter with `name`, `description`, `version`, and `metadata` (openclaw format)
- Overview of what the skill does
- Requirements and setup instructions
- Usage examples (local and stereOS)
- File structure reference
- Customization guide

See the pokemon SKILL.md for the exact frontmatter format:
```yaml
metadata:
  { "openclaw": { "emoji": "...", "requires": { "bins": ["python3"], "env": [] }, "install": [...] } }
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat: add SKILL.md -- openclaw skill definition"
```

---

### Task 9: Create README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Cover: quickstart (stereOS and local), template usage guide (fork, replace agent.py, update jcard.toml), testing instructions, and project structure reference.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quickstart and template usage"
```

---

### Task 10: Run Full Test Suite and Verify Coverage

**Files:**
- All test files

- [ ] **Step 1: Install dev dependencies**

Run: `cd /Users/bdougie/code/papercomputeco/claw-stereo && pip install pytest pytest-cov`

- [ ] **Step 2: Run full test suite with coverage**

Run: `python3 -m pytest --cov --cov-report=term-missing -v`
Expected: All tests pass, 100% coverage on `scripts/` (excluding `observe_cli.py`)

- [ ] **Step 3: Fix any coverage gaps**

If coverage is below 100%, add tests for uncovered lines. Common gaps to check:
- Edge cases in `_parse_content_blob` (None, invalid JSON, non-list JSON)
- All branches in `_summarize_tool_input` (each tool name case)
- Empty session handling in observer

- [ ] **Step 4: Final commit**

```bash
git add tests/
git commit -m "chore: verify full test suite passes with 100% coverage"
```
