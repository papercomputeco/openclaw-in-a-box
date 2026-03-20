import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import Database from "better-sqlite3";
import { TapeReader } from "../src/tape-reader.js";

function createTestDb(dir: string) {
  const dbPath = join(dir, "tapes.sqlite");
  const db = new Database(dbPath);
  db.exec(`
    CREATE TABLE nodes (
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
  `);
  return { db, dbPath };
}

function insertNode(
  db: Database.Database,
  hash: string,
  role: string,
  content: unknown[] | null,
  opts: {
    parentHash?: string;
    createdAt?: string;
    promptTokens?: number;
    completionTokens?: number;
    model?: string;
  } = {}
) {
  db.prepare(
    "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?, NULL)"
  ).run(
    hash,
    role,
    content ? JSON.stringify(content) : null,
    opts.createdAt ?? "2026-03-20T10:00:00Z",
    opts.promptTokens ?? 0,
    opts.completionTokens ?? 0,
    opts.parentHash ?? null,
    opts.model ?? null
  );
}

describe("TapeReader", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "tape-test-"));
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true });
  });

  it("lists sessions (root nodes)", () => {
    const { db, dbPath } = createTestDb(tmpDir);
    insertNode(db, "root1", "user", [{ type: "text", text: "hello" }]);
    insertNode(db, "child1", "assistant", [{ type: "text", text: "hi" }], {
      parentHash: "root1",
      createdAt: "2026-03-20T10:00:01Z",
    });
    db.close();

    const reader = new TapeReader(dbPath);
    expect(reader.listSessions()).toEqual(["root1"]);
  });

  it("reads a session chain", () => {
    const { db, dbPath } = createTestDb(tmpDir);
    insertNode(db, "r1", "user", [{ type: "text", text: "Fix bug" }]);
    insertNode(db, "a1", "assistant", [{ type: "text", text: "Done" }], {
      parentHash: "r1",
      createdAt: "2026-03-20T10:00:01Z",
      promptTokens: 10,
      completionTokens: 20,
    });
    db.close();

    const reader = new TapeReader(dbPath);
    const session = reader.readSession("r1");
    expect(session.entries).toHaveLength(2);
    expect(session.entries[0].type).toBe("user");
    expect(session.entries[0].textContent).toBe("Fix bug");
    expect(session.entries[1].type).toBe("assistant");
    expect(session.entries[1].textContent).toBe("Done");
    expect(session.entries[1].tokenUsage.inputTokens).toBe(10);
    expect(session.entries[1].tokenUsage.outputTokens).toBe(20);
  });

  it("parses tool uses", () => {
    const { db, dbPath } = createTestDb(tmpDir);
    insertNode(db, "r1", "user", [{ type: "text", text: "read file" }]);
    insertNode(
      db,
      "a1",
      "assistant",
      [
        {
          type: "tool_use",
          tool_use_id: "tu1",
          tool_name: "Read",
          tool_input: { file_path: "/tmp/test.py" },
        },
      ],
      { parentHash: "r1", createdAt: "2026-03-20T10:00:01Z" }
    );
    db.close();

    const reader = new TapeReader(dbPath);
    const session = reader.readSession("r1");
    expect(session.entries[1].toolUses).toHaveLength(1);
    expect(session.entries[1].toolUses[0].name).toBe("Read");
    expect(session.entries[1].toolUses[0].inputSummary).toBe("/tmp/test.py");
  });

  it("parses tool results with errors", () => {
    const { db, dbPath } = createTestDb(tmpDir);
    insertNode(db, "r1", "user", [
      {
        type: "tool_result",
        tool_use_id: "tu1",
        content: "not found",
        is_error: true,
      },
    ]);
    db.close();

    const reader = new TapeReader(dbPath);
    const session = reader.readSession("r1");
    expect(session.entries[0].toolResults).toHaveLength(1);
    expect(session.entries[0].toolResults[0].isError).toBe(true);
    expect(session.entries[0].toolResults[0].contentSummary).toBe("not found");
  });

  it("handles null content", () => {
    const { db, dbPath } = createTestDb(tmpDir);
    insertNode(db, "r1", "user", null);
    db.close();

    const reader = new TapeReader(dbPath);
    const session = reader.readSession("r1");
    expect(session.entries[0].textContent).toBe("");
  });

  it("handles empty session", () => {
    const { db, dbPath } = createTestDb(tmpDir);
    db.close();

    const reader = new TapeReader(dbPath);
    const session = reader.readSession("nonexistent");
    expect(session.entries).toHaveLength(0);
    expect(session.startTime).toBe("");
  });
});
