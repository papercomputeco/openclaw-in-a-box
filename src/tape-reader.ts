/**
 * Reader for Tapes SQLite database.
 *
 * Parses conversation nodes from tapes.sqlite into structured objects
 * for analysis. Uses better-sqlite3 for synchronous access.
 */

import Database from "better-sqlite3";

// --- Types ---

export interface ToolUse {
  id: string;
  name: string;
  inputSummary: string;
}

export interface ToolResult {
  toolUseId: string;
  contentSummary: string;
  isError: boolean;
}

export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  cacheCreation: number;
  cacheRead: number;
}

export interface TapeEntry {
  type: string;
  timestamp: string;
  sessionId: string;
  textContent: string;
  toolUses: ToolUse[];
  toolResults: ToolResult[];
  tokenUsage: TokenUsage;
  raw: Record<string, unknown>;
}

export interface TapeSession {
  sessionId: string;
  entries: TapeEntry[];
  startTime: string;
  endTime: string;
}

// --- Content parsing ---

interface ContentBlock {
  type?: string;
  text?: string;
  tool_use_id?: string;
  tool_name?: string;
  tool_input?: unknown;
  content?: unknown;
  is_error?: boolean;
}

function parseContentBlob(blob: unknown): ContentBlock[] {
  if (blob == null) return [];
  try {
    const parsed = typeof blob === "string" ? JSON.parse(blob) : blob;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (b): b is ContentBlock => typeof b === "object" && b !== null
    );
  } catch {
    return [];
  }
}

function summarizeToolInput(name: string, toolInput: unknown): string {
  if (typeof toolInput !== "object" || toolInput === null) {
    return String(toolInput).slice(0, 200);
  }

  const input = toolInput as Record<string, unknown>;

  switch (name) {
    case "Read":
    case "Write":
    case "Edit":
      return String(input.file_path ?? "");
    case "Bash":
      return String(input.command ?? "").slice(0, 200);
    case "Grep":
      return `pattern=${input.pattern ?? ""}`;
    case "Glob":
      return `pattern=${input.pattern ?? ""}`;
    case "Agent":
      return String(input.description ?? "").slice(0, 200);
    default:
      for (const key of ["prompt", "query", "description", "command", "file_path"]) {
        if (key in input) {
          return `${key}=${String(input[key]).slice(0, 200)}`;
        }
      }
      return String(toolInput).slice(0, 200);
  }
}

// --- Row conversion ---

interface NodeRow {
  hash: string;
  role: string | null;
  content: string | null;
  created_at: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cache_creation_input_tokens: number | null;
  cache_read_input_tokens: number | null;
  parent_hash: string | null;
  model: string | null;
  agent_name: string | null;
}

function rowToEntry(row: NodeRow): TapeEntry {
  const role = row.role ?? "";
  const blocks = parseContentBlob(row.content);

  const entry: TapeEntry = {
    type: role,
    timestamp: row.created_at ?? "",
    sessionId: row.hash ?? "",
    textContent: "",
    toolUses: [],
    toolResults: [],
    tokenUsage: { inputTokens: 0, outputTokens: 0, cacheCreation: 0, cacheRead: 0 },
    raw: {
      hash: row.hash,
      role,
      parentHash: row.parent_hash,
      model: row.model,
      agentName: row.agent_name,
    },
  };

  if (role === "assistant") {
    entry.tokenUsage = {
      inputTokens: row.prompt_tokens ?? 0,
      outputTokens: row.completion_tokens ?? 0,
      cacheCreation: row.cache_creation_input_tokens ?? 0,
      cacheRead: row.cache_read_input_tokens ?? 0,
    };

    const texts: string[] = [];
    for (const block of blocks) {
      if (block.type === "text") {
        texts.push(block.text ?? "");
      } else if (block.type === "tool_use") {
        entry.toolUses.push({
          id: block.tool_use_id ?? "",
          name: block.tool_name ?? "",
          inputSummary: summarizeToolInput(
            block.tool_name ?? "",
            block.tool_input ?? {}
          ),
        });
      }
    }
    entry.textContent = texts.join("\n");
  } else if (role === "user") {
    const texts: string[] = [];
    for (const block of blocks) {
      if (block.type === "text") {
        texts.push(block.text ?? "");
      } else if (block.type === "tool_result") {
        let contentSummary = block.content ?? "";
        if (Array.isArray(contentSummary)) {
          contentSummary = contentSummary
            .filter((p): p is Record<string, string> => typeof p === "object" && p !== null)
            .map((p) => p.text ?? "")
            .join("\n");
        }
        entry.toolResults.push({
          toolUseId: block.tool_use_id ?? "",
          contentSummary: String(contentSummary).slice(0, 500),
          isError: Boolean(block.is_error),
        });
      }
    }
    entry.textContent = texts.join("\n");
  }

  return entry;
}

// --- Recursive CTE query ---

const CHAIN_QUERY = `
  WITH RECURSIVE chain(h) AS (
    SELECT ?
    UNION ALL
    SELECT n.hash FROM nodes n
    JOIN chain ON n.parent_hash = chain.h
  )
  SELECT n.hash, n.role, n.content, n.created_at,
    n.prompt_tokens, n.completion_tokens,
    n.cache_creation_input_tokens, n.cache_read_input_tokens,
    n.parent_hash, n.model, n.agent_name
  FROM chain JOIN nodes n ON n.hash = chain.h
  ORDER BY n.created_at
`;

// --- TapeReader class ---

export class TapeReader {
  private dbPath: string;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
  }

  private open(): Database.Database {
    return new Database(this.dbPath, { readonly: true });
  }

  /** Return hashes of root nodes (conversation starts) ordered by time. */
  listSessions(): string[] {
    const db = this.open();
    try {
      const rows = db
        .prepare("SELECT hash FROM nodes WHERE parent_hash IS NULL ORDER BY created_at")
        .all() as { hash: string }[];
      return rows.map((r) => r.hash);
    } finally {
      db.close();
    }
  }

  /** Walk the parent_hash chain from a root node into a TapeSession. */
  readSession(rootHash: string): TapeSession {
    const db = this.open();
    try {
      const rows = db.prepare(CHAIN_QUERY).all(rootHash) as NodeRow[];
      const entries = rows.map(rowToEntry);
      return {
        sessionId: rootHash,
        entries,
        startTime: entries[0]?.timestamp ?? "",
        endTime: entries[entries.length - 1]?.timestamp ?? "",
      };
    } finally {
      db.close();
    }
  }
}
