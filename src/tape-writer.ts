/**
 * Writer for Tapes SQLite database.
 *
 * Inserts conversation nodes into tapes.sqlite. Uses the same 11-column
 * schema that Tapes uses natively.
 */

import Database from "better-sqlite3";
import { createHash } from "crypto";

// --- Types ---

export interface ContentBlock {
  type: string;
  text?: string;
  tool_use_id?: string;
  tool_name?: string;
  tool_input?: unknown;
  content?: unknown;
  is_error?: boolean;
}

export interface WriteNodeOptions {
  role: "user" | "assistant" | "system";
  content: ContentBlock[];
  parentHash?: string | null;
  model?: string | null;
  agentName?: string | null;
  promptTokens?: number;
  completionTokens?: number;
  cacheCreationInputTokens?: number;
  cacheReadInputTokens?: number;
}

// --- Schema ---

const CREATE_TABLE = `
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
`;

const INSERT_NODE = `
  INSERT OR IGNORE INTO nodes (
    hash, role, content, created_at,
    prompt_tokens, completion_tokens,
    cache_creation_input_tokens, cache_read_input_tokens,
    parent_hash, model, agent_name
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`;

// --- Hash generation ---

/** Content-addressable hash for a node. */
function computeHash(
  role: string,
  content: string,
  parentHash: string | null,
  createdAt: string
): string {
  const data = JSON.stringify({ role, content, parentHash, createdAt });
  return createHash("sha256").update(data).digest("hex").slice(0, 16);
}

// --- TapeWriter class ---

export class TapeWriter {
  private dbPath: string;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
  }

  private open(): Database.Database {
    const db = new Database(this.dbPath);
    db.exec(CREATE_TABLE);
    return db;
  }

  /** Initialize the database schema. */
  init(): void {
    const db = this.open();
    db.close();
  }

  /**
   * Write a node to the database.
   * Returns the content-addressable hash of the inserted node.
   */
  writeNode(options: WriteNodeOptions): string {
    const contentJson = JSON.stringify(options.content);
    const createdAt = new Date().toISOString();
    const parentHash = options.parentHash ?? null;
    const hash = computeHash(options.role, contentJson, parentHash, createdAt);

    const db = this.open();
    try {
      db.prepare(INSERT_NODE).run(
        hash,
        options.role,
        contentJson,
        createdAt,
        options.promptTokens ?? 0,
        options.completionTokens ?? 0,
        options.cacheCreationInputTokens ?? 0,
        options.cacheReadInputTokens ?? 0,
        parentHash,
        options.model ?? null,
        options.agentName ?? null
      );
      return hash;
    } finally {
      db.close();
    }
  }

  /** Write a simple text message. Returns the node hash. */
  writeText(
    role: "user" | "assistant",
    text: string,
    parentHash?: string | null
  ): string {
    return this.writeNode({
      role,
      content: [{ type: "text", text }],
      parentHash,
    });
  }
}
