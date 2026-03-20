import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { TapeWriter } from "../src/tape-writer.js";
import { TapeReader } from "../src/tape-reader.js";

describe("TapeWriter", () => {
  let tmpDir: string;
  let dbPath: string;

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "tape-test-"));
    dbPath = join(tmpDir, "tapes.sqlite");
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true });
  });

  it("initializes the database", () => {
    const writer = new TapeWriter(dbPath);
    writer.init();
    // Should be readable by TapeReader
    const reader = new TapeReader(dbPath);
    expect(reader.listSessions()).toEqual([]);
  });

  it("writes a text node", () => {
    const writer = new TapeWriter(dbPath);
    const hash = writer.writeText("user", "Hello world");
    expect(typeof hash).toBe("string");
    expect(hash.length).toBe(16);

    const reader = new TapeReader(dbPath);
    const sessions = reader.listSessions();
    expect(sessions).toHaveLength(1);

    const session = reader.readSession(sessions[0]);
    expect(session.entries[0].textContent).toBe("Hello world");
    expect(session.entries[0].type).toBe("user");
  });

  it("writes a conversation chain", () => {
    const writer = new TapeWriter(dbPath);
    const userHash = writer.writeText("user", "What is 2+2?");
    const assistantHash = writer.writeText("assistant", "4", userHash);

    const reader = new TapeReader(dbPath);
    const session = reader.readSession(userHash);
    expect(session.entries).toHaveLength(2);
    expect(session.entries[0].textContent).toBe("What is 2+2?");
    expect(session.entries[1].textContent).toBe("4");
  });

  it("writes a node with tool use content", () => {
    const writer = new TapeWriter(dbPath);
    const userHash = writer.writeText("user", "read a file");
    const hash = writer.writeNode({
      role: "assistant",
      content: [
        {
          type: "tool_use",
          tool_use_id: "tu1",
          tool_name: "Read",
          tool_input: { file_path: "/tmp/test.ts" },
        },
      ],
      parentHash: userHash,
      model: "claude-3",
      promptTokens: 100,
      completionTokens: 50,
    });

    const reader = new TapeReader(dbPath);
    const session = reader.readSession(userHash);
    expect(session.entries[1].toolUses).toHaveLength(1);
    expect(session.entries[1].toolUses[0].name).toBe("Read");
    expect(session.entries[1].tokenUsage.inputTokens).toBe(100);
  });

  it("produces unique hashes for different content", () => {
    const writer = new TapeWriter(dbPath);
    const h1 = writer.writeText("user", "Hello");
    const h2 = writer.writeText("user", "World");
    expect(h1).not.toBe(h2);
  });
});
