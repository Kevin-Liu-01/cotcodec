#!/usr/bin/env bun
/** Zero-model falsification doctor for Magic Context's chronological pager. */

import { createHash } from "node:crypto";
import {
    existsSync,
    mkdirSync,
    readFileSync,
    readdirSync,
    statSync,
} from "node:fs";
import { join } from "node:path";

import {
    appendCompartments,
    getCompartments,
} from "/opt/magic-context/packages/plugin/src/features/magic-context/compartment-storage.ts";
import { initializeDatabase } from "/opt/magic-context/packages/plugin/src/features/magic-context/storage-db.ts";
import { runMigrations } from "/opt/magic-context/packages/plugin/src/features/magic-context/migrations.ts";
import { clearSession } from "/opt/magic-context/packages/plugin/src/features/magic-context/storage-meta-session.ts";
import { renderDecayedCompartments } from "/opt/magic-context/packages/plugin/src/hooks/magic-context/decay-render.ts";
import { closeReadOnlySessionDb } from "/opt/magic-context/packages/plugin/src/hooks/magic-context/read-session-db.ts";
import { setHarness } from "/opt/magic-context/packages/plugin/src/shared/harness.ts";
import { Database } from "/opt/magic-context/packages/plugin/src/shared/sqlite.ts";
import {
    renderMessageByOrdinal,
    renderVerboseRange,
} from "/opt/magic-context/packages/plugin/src/tools/ctx-expand/render.ts";

const STATE_ROOT = "/state";
const MAGIC_DB = join(STATE_ROOT, "magic-context.db");
const RAW_DB = join(STATE_ROOT, "xdg", "opencode", "opencode.db");
const SESSION_A = "cotcodec-magic-session-a";
const SESSION_B = "cotcodec-magic-session-b";
const SUPPORTED_CANARY = "SUPPORTED-CANARY-QUARTZ-αβ";
const TOOL_CANARY = "TOOL-CANARY-COBALT-完整";
const REASONING_CANARY = "REASONING-CANARY-MUST-NOT-RECOVER";
const OTHER_SESSION_CANARY = "SESSION-B-CANARY-UMBER";
const COMPARTMENT_CANARY = "COMPARTMENT-CANARY-SAFFRON";
const FORBIDDEN_SECRETS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "VOYAGE_API_KEY",
    "COHERE_API_KEY",
];

function fail(message: string): never {
    throw new Error(message);
}

function sha256(value: string | Uint8Array): string {
    return createHash("sha256").update(value).digest("hex");
}

function canonical(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(canonical);
    if (value !== null && typeof value === "object") {
        return Object.fromEntries(
            Object.entries(value as Record<string, unknown>)
                .sort(([left], [right]) => left.localeCompare(right))
                .map(([key, child]) => [key, canonical(child)]),
        );
    }
    return value;
}

function digest(value: unknown): string {
    return sha256(JSON.stringify(canonical(value)));
}

function assertContainedInputs(): void {
    const present = FORBIDDEN_SECRETS.filter((name) => process.env[name]);
    if (present.length > 0) fail(`provider secrets are forbidden: ${present.join(",")}`);
    if (process.env.XDG_DATA_HOME !== join(STATE_ROOT, "xdg")) {
        fail("XDG_DATA_HOME must point at the isolated state volume");
    }
}

function makeCompartments() {
    return Array.from({ length: 52 }, (_, index) => {
        const ordinal = index + 1;
        const marker = index === 0 ? COMPARTMENT_CANARY : `COMPARTMENT-${ordinal}`;
        return {
            sequence: ordinal,
            startMessage: ordinal,
            endMessage: ordinal,
            startMessageId: `compartment-start-${ordinal}`,
            endMessageId: `compartment-end-${ordinal}`,
            title: `Work arc ${ordinal}`,
            content: `${marker} full narrative ${"detail ".repeat(40)}`,
            p1: `P1 ${marker} ${"full detail ".repeat(80)}`,
            p2: `P2 ${marker} ${"summary ".repeat(40)}`,
            p3: `P3 ${marker} ${"brief ".repeat(20)}`,
            p4: `P4 ${marker} anchor`,
            importance: 50,
            episodeType: "doctor",
        };
    });
}

function createRawDatabase(): void {
    mkdirSync(join(STATE_ROOT, "xdg", "opencode"), { recursive: true, mode: 0o700 });
    const db = new Database(RAW_DB);
    try {
        db.exec(`
            CREATE TABLE message (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                time_created INTEGER NOT NULL,
                time_updated INTEGER NOT NULL,
                data TEXT NOT NULL
            );
            CREATE TABLE part (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                time_created INTEGER NOT NULL,
                time_updated INTEGER NOT NULL,
                data TEXT NOT NULL
            );
        `);
        const message = db.prepare(
            "INSERT INTO message (id, session_id, time_created, time_updated, data) VALUES (?, ?, ?, ?, ?)",
        );
        const part = db.prepare(
            "INSERT INTO part (id, session_id, message_id, time_created, time_updated, data) VALUES (?, ?, ?, ?, ?, ?)",
        );
        message.run("a-user", SESSION_A, 1, 1, JSON.stringify({ role: "user" }));
        part.run(
            "a-user-text",
            SESSION_A,
            "a-user",
            1,
            1,
            JSON.stringify({ type: "text", text: `Operator text ${SUPPORTED_CANARY}` }),
        );
        message.run("a-tool", SESSION_A, 2, 2, JSON.stringify({ role: "assistant" }));
        part.run(
            "a-tool-reasoning",
            SESSION_A,
            "a-tool",
            2,
            2,
            JSON.stringify({ type: "reasoning", text: REASONING_CANARY }),
        );
        part.run(
            "a-tool-output",
            SESSION_A,
            "a-tool",
            3,
            3,
            JSON.stringify({
                type: "tool",
                tool: "read",
                callID: "doctor:1",
                state: {
                    title: "Read diagnostic",
                    input: { filePath: "/fixture/diagnostic.txt" },
                    output: `${TOOL_CANARY}\n${"untruncated-line\n".repeat(80)}`,
                },
            }),
        );
        message.run("b-user", SESSION_B, 1, 1, JSON.stringify({ role: "user" }));
        part.run(
            "b-user-text",
            SESSION_B,
            "b-user",
            1,
            1,
            JSON.stringify({ type: "text", text: OTHER_SESSION_CANARY }),
        );
    } finally {
        db.close();
    }
}

function readMagicProjection() {
    const db = new Database(MAGIC_DB);
    try {
        const sessionA = getCompartments(db, SESSION_A);
        const sessionB = getCompartments(db, SESSION_B);
        const wide = renderDecayedCompartments({
            compartments: sessionA,
            historyBudgetTokens: 100_000,
        });
        const tight = renderDecayedCompartments({
            compartments: sessionA,
            historyBudgetTokens: 300,
        });
        return {
            session_a_rows: sessionA.length,
            session_b_rows: sessionB.length,
            stored_oldest_canary: sessionA[0]?.p1?.includes(COMPARTMENT_CANARY) === true,
            wide_contains_oldest: wide.includes(COMPARTMENT_CANARY),
            tight_omits_oldest: !tight.includes(COMPARTMENT_CANARY),
            tight_contains_newest: tight.includes("COMPARTMENT-52"),
            wide_sha256: sha256(wide),
            tight_sha256: sha256(tight),
        };
    } finally {
        db.close();
    }
}

function readExpansionProjection() {
    closeReadOnlySessionDb();
    const user = renderMessageByOrdinal(SESSION_A, 1);
    const tool = renderMessageByOrdinal(SESSION_A, 2);
    const other = renderMessageByOrdinal(SESSION_B, 1);
    const verbose = renderVerboseRange(SESSION_A, 1, 2, 30);
    return {
        supported_text_preserved: user.includes(SUPPORTED_CANARY),
        tool_input_preserved: tool.includes("/fixture/diagnostic.txt"),
        tool_output_preserved_untruncated:
            tool.includes(TOOL_CANARY) && tool.match(/untruncated-line/g)?.length === 80,
        reasoning_stripped: !tool.includes(REASONING_CANARY),
        session_a_excludes_b: !user.includes(OTHER_SESSION_CANARY) && !tool.includes(OTHER_SESSION_CANARY),
        session_b_contains_b: other.includes(OTHER_SESSION_CANARY),
        verbose_truncated: verbose.truncated,
        verbose_last_ordinal: verbose.lastOrdinal,
        user_sha256: sha256(user),
        tool_sha256: sha256(tool),
        other_sha256: sha256(other),
    };
}

function prepare() {
    if (existsSync(MAGIC_DB) || existsSync(RAW_DB)) fail("prepare requires an empty state volume");
    mkdirSync(STATE_ROOT, { recursive: true, mode: 0o700 });
    createRawDatabase();
    const rawBefore = sha256(readFileSync(RAW_DB));
    const db = new Database(MAGIC_DB);
    try {
        initializeDatabase(db);
        runMigrations(db);
        appendCompartments(db, SESSION_A, makeCompartments());
        appendCompartments(db, SESSION_B, [
            {
                sequence: 1,
                startMessage: 1,
                endMessage: 1,
                startMessageId: "b-start",
                endMessageId: "b-end",
                title: "Session B",
                content: OTHER_SESSION_CANARY,
                p1: OTHER_SESSION_CANARY,
                p2: OTHER_SESSION_CANARY,
                p3: OTHER_SESSION_CANARY,
                p4: OTHER_SESSION_CANARY,
                importance: 50,
                episodeType: "doctor",
            },
        ]);
    } finally {
        db.close();
    }
    const paging = readMagicProjection();
    const expansion = readExpansionProjection();
    const rawAfter = sha256(readFileSync(RAW_DB));
    if (
        paging.session_a_rows !== 52 ||
        !paging.stored_oldest_canary ||
        !paging.wide_contains_oldest ||
        !paging.tight_omits_oldest ||
        !paging.tight_contains_newest
    ) fail("deterministic compartment paging contract failed");
    if (
        !expansion.supported_text_preserved ||
        !expansion.tool_input_preserved ||
        !expansion.tool_output_preserved_untruncated ||
        !expansion.reasoning_stripped ||
        !expansion.session_a_excludes_b ||
        !expansion.session_b_contains_b ||
        !expansion.verbose_truncated
    ) fail("supported expansion projection contract failed");
    if (rawBefore !== rawAfter) fail("read-only paging changed the host raw DB");
    const projection = { paging, expansion, raw_db_unchanged: true };
    return {
        phase: "prepare",
        claim: "host-backed-chronological-wire-paging-and-supported-projection-only",
        projection,
        projection_sha256: digest(projection),
        model_calls: 0,
        embedding_calls: 0,
        network_calls: 0,
    };
}

function restart() {
    if (!existsSync(MAGIC_DB) || !existsSync(RAW_DB)) fail("restart state is missing");
    const paging = readMagicProjection();
    const expansion = readExpansionProjection();
    const projection = { paging, expansion, raw_db_unchanged: true };
    return {
        phase: "restart",
        projection,
        projection_sha256: digest(projection),
        supported_projection_not_raw_json: true,
        host_storage_required: true,
    };
}

function alias() {
    setHarness("pi");
    const db = new Database(MAGIC_DB);
    let canRead = false;
    try {
        canRead = getCompartments(db, SESSION_A).some((row) => row.p1?.includes(COMPARTMENT_CANARY));
    } finally {
        db.close();
    }
    if (!canRead) fail("expected cross-harness same-session-id alias was not reproduced");
    return {
        phase: "alias",
        same_session_id_cross_harness_alias_reproduced: canRead,
        security_tenancy_boundary_supported: false,
        portable_lifecycle_admission: "blocked",
    };
}

function scanCanaries(): Array<{ file: string; canary_sha256: string }> {
    const canaries = [SUPPORTED_CANARY, TOOL_CANARY, COMPARTMENT_CANARY];
    const hits: Array<{ file: string; canary_sha256: string }> = [];
    for (const file of readdirSync(STATE_ROOT)) {
        const path = join(STATE_ROOT, file);
        if (!statSync(path).isFile()) continue;
        const bytes = readFileSync(path);
        for (const canary of canaries) {
            if (bytes.includes(Buffer.from(canary))) {
                hits.push({ file, canary_sha256: sha256(canary) });
            }
        }
    }
    for (const suffix of ["", "-wal", "-shm"]) {
        const path = `${RAW_DB}${suffix}`;
        if (!existsSync(path) || !statSync(path).isFile()) continue;
        const bytes = readFileSync(path);
        for (const canary of canaries) {
            if (bytes.includes(Buffer.from(canary))) {
                hits.push({ file: `xdg/opencode/opencode.db${suffix}`, canary_sha256: sha256(canary) });
            }
        }
    }
    return hits.sort((left, right) => `${left.file}${left.canary_sha256}`.localeCompare(`${right.file}${right.canary_sha256}`));
}

function purge() {
    const db = new Database(MAGIC_DB);
    try {
        clearSession(db, SESSION_A);
        if (getCompartments(db, SESSION_A).length !== 0) fail("logical session rows remain");
        if (getCompartments(db, SESSION_B).length !== 1) fail("session B was damaged by session A clear");
    } finally {
        db.close();
    }

    closeReadOnlySessionDb();
    const host = new Database(RAW_DB);
    try {
        host.prepare("DELETE FROM part WHERE session_id = ? AND message_id = ?").run(SESSION_A, "a-tool");
        host.prepare("DELETE FROM message WHERE session_id = ? AND id = ?").run(SESSION_A, "a-tool");
    } finally {
        host.close();
    }
    closeReadOnlySessionDb();
    const missing = renderMessageByOrdinal(SESSION_A, 2);
    if (!missing.includes("can't be recovered") || missing.includes(TOOL_CANARY)) {
        fail("host deletion did not make expansion explicitly unrecoverable");
    }
    closeReadOnlySessionDb();
    const hits = scanCanaries();
    if (hits.length === 0) fail("expected physical residue was not reproduced");
    return {
        phase: "purge",
        plugin_logical_session_a_rows: 0,
        session_b_rows: 1,
        host_row_deletion_makes_expansion_unrecoverable: true,
        native_secure_purge_supported: false,
        physical_zero_residue: false,
        physical_hits: hits,
    };
}

assertContainedInputs();
const phase = process.argv[2];
const result =
    phase === "prepare"
        ? prepare()
        : phase === "restart"
          ? restart()
          : phase === "alias"
            ? alias()
            : phase === "purge"
              ? purge()
              : fail("usage: doctor.ts prepare|restart|alias|purge");
process.stdout.write(`${JSON.stringify(canonical(result))}\n`);
