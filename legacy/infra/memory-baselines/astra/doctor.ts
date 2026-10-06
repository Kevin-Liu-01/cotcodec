#!/usr/bin/env node
/** Native ASTRA lifecycle falsifier. No model or external embedding is used. */

import { createHash } from "node:crypto";

import { createPool } from "/opt/astra/src/db.ts";
import { FakeEmbedder } from "/opt/astra/src/embedder.ts";
import { MemoryWindow } from "/opt/astra/src/memory-window.ts";
import { runMigrations } from "/opt/astra/src/migrate.ts";
import { MemoryStore, type Memory } from "/opt/astra/src/store.ts";

const USER_A = "00000000-0000-0000-0000-00000000a001";
const USER_B = "00000000-0000-0000-0000-00000000b001";
const T0 = new Date("2026-08-15T12:00:00.000Z");
const T1 = new Date("2026-08-15T12:05:00.000Z");
const EXPECTED_STATUS = "BLOCKED_NATIVE_PURGE_IDEMPOTENCY_AND_PINNED_CAP";
const FORBIDDEN_SECRET_NAMES = [
  "ANTHROPIC_API_KEY",
  "OPENAI_API_KEY",
  "VOYAGE_API_KEY",
  "COHERE_API_KEY",
  "GEMINI_API_KEY",
  "AWS_ACCESS_KEY_ID",
  "AWS_SECRET_ACCESS_KEY",
];

function fail(message: string): never {
  throw new Error(message);
}

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, child]) => [key, canonical(child)]),
    );
  }
  return value;
}

function digest(value: unknown): string {
  return createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex");
}

function itemContent(index: number): string {
  const id = index.toString().padStart(2, "0");
  return `astra pager item ${id} quartz-${id}`;
}

function assertNoSecrets(): void {
  const present = FORBIDDEN_SECRET_NAMES.filter((name) => process.env[name]);
  if (present.length > 0) fail(`provider secrets are forbidden: ${present.join(",")}`);
}

async function connect() {
  const raw = process.env.ASTRA_DB_URL;
  if (!raw) fail("ASTRA_DB_URL is required");
  const databaseUrl = new URL(raw);
  const databaseName = databaseUrl.pathname.slice(1);
  if (databaseName !== "astra") fail("ASTRA_DB_URL must target the astra database");
  const adminUrl = new URL(databaseUrl);
  adminUrl.pathname = "/defaultdb";
  const admin = createPool(adminUrl.toString());
  await admin.query("CREATE DATABASE IF NOT EXISTS astra");
  await admin.end();
  const pool = createPool(databaseUrl.toString());
  await runMigrations(pool);
  return pool;
}

async function sourceMap(pool: ReturnType<typeof createPool>): Promise<Map<string, string>> {
  const rows = await pool.query("SELECT id, source_context FROM memories");
  return new Map(rows.rows.map((row) => [String(row.id), String(row.source_context)]));
}

async function stableProjection(pool: ReturnType<typeof createPool>) {
  const rows = await pool.query(
    `SELECT id, user_id, source_context, content, access_count,
            deleted_at IS NOT NULL AS deleted
       FROM memories ORDER BY source_context, id`,
  );
  const idToSource = new Map(rows.rows.map((row) => [String(row.id), String(row.source_context)]));
  const sessions = await pool.query(
    `SELECT user_id, context, turn, window_entries, updated_at
       FROM session_state ORDER BY user_id`,
  );
  const grouped = new Map<string, { count: number; deleted: number; access: number; content: string }>();
  for (const row of rows.rows) {
    const key = `${row.user_id}:${row.source_context}`;
    const current = grouped.get(key) ?? { count: 0, deleted: 0, access: 0, content: String(row.content) };
    current.count += 1;
    current.deleted += row.deleted ? 1 : 0;
    current.access += Number(row.access_count);
    grouped.set(key, current);
  }
  return {
    memories: [...grouped.entries()].map(([key, value]) => ({
      key,
      count: value.count,
      deleted: value.deleted,
      access_count: value.access,
      content_sha256: digest(value.content),
    })),
    sessions: sessions.rows.map((row) => ({
      user: String(row.user_id) === USER_A ? "user-a" : "user-b",
      context: row.context,
      turn: Number(row.turn),
      window_sources: (row.window_entries as Array<{ memoryId: string }>).map((entry) => {
        const source = idToSource.get(entry.memoryId);
        if (!source) fail(`session references unknown memory ${entry.memoryId}`);
        return source;
      }),
      updated_at: new Date(row.updated_at).toISOString(),
    })),
  };
}

function assertWindowSources(
  window: MemoryWindow,
  byId: Map<string, string>,
  expected: string[],
): void {
  const actual = window.serialize().map((entry) => byId.get(entry.memoryId));
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    fail(`window mismatch: ${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
  }
}

async function prepare() {
  const pool = await connect();
  try {
    const store = new MemoryStore(pool, new FakeEmbedder());
    const memories: Memory[] = [];
    for (let index = 0; index < 13; index += 1) {
      memories.push(
        await store.remember({
          userId: USER_A,
          context: "lab",
          memoryType: "semantic",
          content: itemContent(index),
          importance: 0.5,
          privacyLevel: "private",
          sourceContext: `event-${index.toString().padStart(2, "0")}`,
          createdAt: T0,
        }),
      );
    }

    const window = new MemoryWindow();
    for (let index = 0; index < memories.length; index += 1) {
      window.admit(memories[index]!, { score: 0.5, turn: index + 1, via: "passive" });
    }
    if (window.size !== 12 || window.has(memories[0]!.id)) {
      fail("default unpinned K=12 eviction did not remove the oldest item");
    }
    if (!(await store.get(memories[0]!.id, USER_A))) {
      fail("evicted active item disappeared from durable memory");
    }
    const [recalled] = await store.recall({
      userId: USER_A,
      query: itemContent(0),
      context: "lab",
      topK: 1,
      now: T0,
    });
    if (!recalled || recalled.id !== memories[0]!.id) fail("exact durable recall missed event-00");
    window.admit(recalled, { score: recalled.score, turn: 14, via: "tool" });
    if (window.size !== 12 || window.has(memories[1]!.id) || !window.has(memories[0]!.id)) {
      fail("retrieval-driven re-admission did not evict event-01");
    }
    await store.saveSessionState(
      {
        userId: USER_A,
        context: "lab",
        turn: 14,
        windowEntries: window.serialize(),
        transcript: [],
        digest: "",
        openThreads: [],
      },
      T0,
    );

    const userBMemory = await store.remember({
      userId: USER_B,
      context: "lab",
      memoryType: "semantic",
      content: "astra user b cobalt isolation marker",
      sourceContext: "user-b-event",
      createdAt: T0,
    });
    const userBWindow = new MemoryWindow();
    userBWindow.admit(userBMemory, { score: 0.5, turn: 1, via: "passive" });
    await store.saveSessionState(
      {
        userId: USER_B,
        context: "lab",
        turn: 1,
        windowEntries: userBWindow.serialize(),
        transcript: [],
        digest: "",
        openThreads: [],
      },
      T0,
    );
    const crossUser = await store.recall({
      userId: USER_A,
      query: "cobalt isolation marker",
      context: "lab",
      topK: 5,
      now: T0,
    });
    if (crossUser.some((memory) => memory.id === userBMemory.id)) fail("user isolation failed");

    const duplicateInput = {
      userId: USER_A,
      context: "lab",
      memoryType: "semantic" as const,
      content: "astra duplicate retry saffron marker",
      sourceContext: "duplicate-retry",
      createdAt: T0,
    };
    const duplicateA = await store.remember(duplicateInput);
    const duplicateB = await store.remember(duplicateInput);
    if (duplicateA.id === duplicateB.id) fail("duplicate writes unexpectedly shared one identity");

    const pinned = new MemoryWindow();
    memories.forEach((memory, index) =>
      pinned.admit(memory, { score: 0.5, turn: index + 1, via: "pin", pinned: true }),
    );
    if (pinned.size !== 13) fail("all-pinned overflow diagnostic did not exceed K=12");

    const byId = await sourceMap(pool);
    assertWindowSources(window, byId, [
      "event-02", "event-03", "event-04", "event-05", "event-06", "event-07",
      "event-08", "event-09", "event-10", "event-11", "event-12", "event-00",
    ]);
    const projection = await stableProjection(pool);
    return {
      phase: "prepare",
      bounded_unpinned_window: true,
      evicted_memory_remains_durable: true,
      retrieval_driven_readmission: true,
      user_isolation: true,
      duplicate_write_creates_distinct_rows: true,
      duplicate_native_ids: 2,
      all_pinned_window_size: pinned.size,
      all_pinned_window_exceeds_capacity: true,
      projection,
      projection_sha256: digest(projection),
    };
  } finally {
    await pool.end();
  }
}

async function restart() {
  const pool = await connect();
  try {
    const store = new MemoryStore(pool, new FakeEmbedder());
    const stateA = await store.loadSessionState(USER_A);
    const stateB = await store.loadSessionState(USER_B);
    if (!stateA || !stateB) fail("acknowledged session state did not survive restart");
    const memories = await store.getMany(stateA.windowEntries.map((entry) => entry.memoryId));
    const restored = MemoryWindow.restore(stateA.windowEntries, new Map(memories.map((m) => [m.id, m])));
    const byId = await sourceMap(pool);
    assertWindowSources(restored, byId, [
      "event-02", "event-03", "event-04", "event-05", "event-06", "event-07",
      "event-08", "event-09", "event-10", "event-11", "event-12", "event-00",
    ]);
    const event01 = await pool.query(
      "SELECT id FROM memories WHERE user_id = $1 AND source_context = 'event-01'",
      [USER_A],
    );
    const event01Id = String(event01.rows[0]?.id ?? "");
    const [recalled] = await store.recall({
      userId: USER_A,
      query: itemContent(1),
      context: "lab",
      topK: 1,
      now: T1,
    });
    if (!recalled || recalled.id !== event01Id) fail("post-restart recall missed event-01");
    restored.admit(recalled, { score: recalled.score, turn: 15, via: "tool" });
    assertWindowSources(restored, byId, [
      "event-03", "event-04", "event-05", "event-06", "event-07", "event-08",
      "event-09", "event-10", "event-11", "event-12", "event-00", "event-01",
    ]);
    await store.saveSessionState({ ...stateA, turn: 15, windowEntries: restored.serialize() }, T1);

    const event12 = await pool.query(
      "SELECT id, content FROM memories WHERE user_id = $1 AND source_context = 'event-12'",
      [USER_A],
    );
    const event12Id = String(event12.rows[0]?.id ?? "");
    const event12Content = String(event12.rows[0]?.content ?? "");
    await store.forget(event12Id, USER_A);
    if (await store.get(event12Id, USER_A)) fail("soft-deleted memory remains logically visible");
    const deletedRecall = await store.recall({
      userId: USER_A,
      query: event12Content,
      context: "lab",
      topK: 5,
      now: T1,
    });
    if (deletedRecall.some((memory) => memory.id === event12Id)) {
      fail("soft-deleted memory remains recall-visible");
    }
    const rawDeleted = await pool.query(
      "SELECT content, deleted_at FROM memories WHERE id = $1",
      [event12Id],
    );
    if (
      rawDeleted.rows.length !== 1 ||
      String(rawDeleted.rows[0].content) !== event12Content ||
      rawDeleted.rows[0].deleted_at === null
    ) {
      fail("soft-delete residue diagnostic did not preserve the plaintext row");
    }
    const stateAfterDelete = await store.loadSessionState(USER_A);
    if (!stateAfterDelete?.windowEntries.some((entry) => entry.memoryId === event12Id)) {
      fail("session-state soft-delete reference was unexpectedly removed");
    }
    if ((await store.loadSessionState(USER_B))?.windowEntries.length !== 1) {
      fail("user-b state changed during user-a restart/delete path");
    }

    const projection = await stableProjection(pool);
    return {
      phase: "restart",
      terminal_status: EXPECTED_STATUS,
      forced_restart_preserves_acknowledged_state: true,
      retrieval_driven_readmission: true,
      user_isolation: true,
      soft_deleted_plaintext_row_remains: true,
      deleted_content_sha256: digest(event12Content),
      session_state_retains_soft_deleted_reference: true,
      native_physical_user_purge_available: false,
      native_idempotency_key_available: false,
      projection,
      projection_sha256: digest(projection),
    };
  } finally {
    await pool.end();
  }
}

async function main() {
  assertNoSecrets();
  const phase = process.argv[2];
  const result = phase === "prepare" ? await prepare() : phase === "restart" ? await restart() : fail("phase must be prepare or restart");
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.stack : String(error)}\n`);
  process.exitCode = 1;
});
