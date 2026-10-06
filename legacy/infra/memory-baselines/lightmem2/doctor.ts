#!/usr/bin/env -S node --import tsx
/** Contained lifecycle and isolation falsifier for pinned LightMem2/TokenPilot. */

import { createHash } from "node:crypto";
import {
  closeSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readFileSync,
  readdirSync,
  statSync,
  writeSync,
} from "node:fs";
import { join } from "node:path";

import {
  archiveContent,
  createFileSystemArtifactStore,
  readArchive,
  renderRecoveredArchive,
  resolveArchivePathAcrossSessions,
  resolveArchivePathFromLookup,
} from "/opt/lightmem2/source/components/packages/foundation/artifact-store/src/index.ts";
import { applyCanonicalEviction } from "/opt/lightmem2/source/components/packages/features/eviction/src/history-apply.ts";

const SCHEMA_VERSION = 1;
const TERMINAL_STATUS = "BLOCKED_CROSS_SESSION_DISCLOSURE_ARCHIVE_COLLISION_AND_NO_NATIVE_PURGE";

type JsonObject = Record<string, unknown>;

class DoctorError extends Error {}

function asRecord(value: unknown): JsonObject | undefined {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as JsonObject
    : undefined;
}

function canonicalBytes(value: unknown): Buffer {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`);
}

function writeOnce(path: string, value: unknown): void {
  mkdirSync(join(path, ".."), { recursive: true });
  const flags = 0x1 | 0x40 | 0x80 | (process.platform === "linux" ? 0x20000 : 0);
  const fd = openSync(path, flags, 0o600);
  try {
    const data = canonicalBytes(value);
    let offset = 0;
    while (offset < data.length) offset += writeSync(fd, data, offset);
    fsyncSync(fd);
  } finally {
    closeSync(fd);
  }
}

function readObject(path: string): JsonObject {
  const value = JSON.parse(readFileSync(path, "utf8"));
  if (!asRecord(value)) throw new DoctorError(`expected JSON object: ${path}`);
  return value as JsonObject;
}

function sha256(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function walkFiles(root: string): string[] {
  const output: string[] = [];
  const visit = (path: string): void => {
    for (const name of readdirSync(path).sort()) {
      const child = join(path, name);
      const stats = statSync(child);
      if (stats.isDirectory()) visit(child);
      else if (stats.isFile()) output.push(child);
    }
  };
  visit(root);
  return output;
}

function contentToText(value: unknown): string {
  if (typeof value === "string") return value;
  if (!Array.isArray(value)) return "";
  return value.map((item) => {
    const block = asRecord(item);
    return typeof block?.text === "string" ? block.text : "";
  }).join("");
}

function ensureContextSafeDetails(details: unknown, patch: JsonObject): JsonObject {
  const prior = asRecord(details) ?? {};
  const contextSafe = asRecord(prior.contextSafe) ?? {};
  return { ...prior, contextSafe: { ...contextSafe, ...patch } };
}

function canonicalMessageTaskIds(message: JsonObject): string[] {
  const contextSafe = asRecord(asRecord(message.details)?.contextSafe);
  return Array.isArray(contextSafe?.taskIds)
    ? contextSafe.taskIds.filter((item): item is string => typeof item === "string")
    : [];
}

async function unscopedRecover(dataKey: string, stateDir: string): Promise<string> {
  const archivePath = await resolveArchivePathAcrossSessions(dataKey, stateDir);
  const archive = archivePath ? await readArchive(archivePath) : null;
  return archive ? renderRecoveredArchive({ dataKey, archive }).text : "";
}

function base(phase: string, repeat: number): JsonObject {
  return {
    schema_version: SCHEMA_VERSION,
    phase,
    repeat,
    scientific_result: false,
    publication_ready: false,
    model_calls: 0,
    embedding_model_calls: 0,
    external_api_calls: 0,
  };
}

async function prepare(stateRoot: string, repeat: number): Promise<JsonObject> {
  const contractPath = join(stateRoot, "contract.json");
  if (readdirSync(stateRoot).length !== 0) throw new DoctorError("prepare refuses existing state");
  const aCanary = `LIGHTMEM2_SESSION_A_R${repeat}_CANARY_4A6C`;
  const bCanary = `LIGHTMEM2_SESSION_B_R${repeat}_SECRET_9D31`;
  const collisionFirst = `LIGHTMEM2_COLLISION_FIRST_R${repeat}_21AA`;
  const collisionSecond = `LIGHTMEM2_COLLISION_SECOND_R${repeat}_98BB`;
  const sessionAArchive = join(stateRoot, "tokenpilot", "tool-result-archives", "session-a");
  const sessionBArchive = join(stateRoot, "tokenpilot", "tool-result-archives", "session-b");

  const messages = [{
    role: "assistant",
    content: [{ type: "text", text: aCanary }],
    details: { contextSafe: { taskIds: ["task-a"], turnAbsId: "session-a:t1" } },
  }];
  const eviction = await applyCanonicalEviction({
    stateDir: stateRoot,
    sessionId: "session-a",
    messages,
    registry: { evictableTaskIds: ["task-a"], tasks: { "task-a": { title: "private alpha" } } },
    enabled: true,
    policy: "registered-test",
    minBlockChars: 1,
    replacementMode: "pointer_stub",
    archiveDir: sessionAArchive,
    persistedBy: "cotcodec-lightmem2-doctor",
    archiveSourceLabel: "canonical_eviction",
    helpers: {
      asRecord,
      appendTaskStateTrace: async () => undefined,
      canonicalMessageTaskIds,
      contentToText,
      dedupeStrings: (values) => [...new Set(values)],
      ensureContextSafeDetails,
      extractPathLike: () => undefined,
      extractToolMessageText: (message) => contentToText(message.content),
      isToolResultLikeMessage: () => false,
      messageToolCallId: () => undefined,
      safeId: (value) => value.replace(/[^a-zA-Z0-9._-]+/g, "_"),
    },
  });
  const stub = asRecord(eviction.messages[0]);
  const contextSafe = asRecord(asRecord(stub?.details)?.contextSafe);
  const evictionDetails = asRecord(contextSafe?.eviction);
  const aArchivePath = String(evictionDetails?.archivePath ?? "");
  const aDataKey = String(evictionDetails?.dataKey ?? "");
  const aArchive = await readArchive(aArchivePath);

  const bLocation = await archiveContent({
    sessionId: "session-b",
    segmentId: "private-b",
    sourcePass: "cotcodec_isolation_probe",
    toolName: "read",
    dataKey: `session-b-private-r${repeat}`,
    originalText: bCanary,
    archiveDir: sessionBArchive,
  });
  const strictWrongSession = await resolveArchivePathFromLookup(
    `session-b-private-r${repeat}`,
    stateRoot,
    "session-a",
  );
  const unscopedRecovery = await unscopedRecover(`session-b-private-r${repeat}`, stateRoot);

  const originalDateNow = Date.now;
  let collisionPathOne = "";
  let collisionPathTwo = "";
  try {
    Date.now = () => 1_786_852_800_000 + repeat;
    collisionPathOne = (await archiveContent({
      sessionId: "session-a",
      segmentId: "same-segment",
      sourcePass: "cotcodec_collision_probe",
      toolName: "read",
      dataKey: `collision-first-r${repeat}`,
      originalText: collisionFirst,
      archiveDir: sessionAArchive,
    })).archivePath;
    collisionPathTwo = (await archiveContent({
      sessionId: "session-a",
      segmentId: "same-segment",
      sourcePass: "cotcodec_collision_probe",
      toolName: "read",
      dataKey: `collision-second-r${repeat}`,
      originalText: collisionSecond,
      archiveDir: sessionAArchive,
    })).archivePath;
  } finally {
    Date.now = originalDateNow;
  }
  const firstLookup = await resolveArchivePathFromLookup(
    `collision-first-r${repeat}`,
    stateRoot,
    "session-a",
  );
  const firstResolved = firstLookup ? await readArchive(firstLookup) : null;

  const contract = {
    schema_version: SCHEMA_VERSION,
    repeat,
    a_canary: aCanary,
    b_canary: bCanary,
    collision_first: collisionFirst,
    collision_second: collisionSecond,
    a_archive_path: aArchivePath,
    a_data_key: aDataKey,
    b_archive_path: bLocation.archivePath,
    b_data_key: `session-b-private-r${repeat}`,
  };
  writeOnce(contractPath, contract);
  return {
    ...base("prepare", repeat),
    archive_before_stub_succeeded: (
      eviction.changed
      && eviction.appliedCount === 1
      && contentToText(stub?.content).includes("Completed task paged out")
      && !contentToText(stub?.content).includes(aCanary)
      && aArchive?.originalText.includes(aCanary) === true
    ),
    strict_session_lookup_rejected_other_session: strictWrongSession === null,
    unscoped_mcp_resolver_recovered_other_session: unscopedRecovery.includes(bCanary),
    archive_filename_collision_reused_path: collisionPathOne === collisionPathTwo,
    first_key_resolved_to_second_payload: (
      firstResolved?.dataKey === `collision-second-r${repeat}`
      && firstResolved.originalText === collisionSecond
    ),
    contract_sha256: sha256(contractPath),
  };
}

async function verifyRestart(stateRoot: string, repeat: number): Promise<JsonObject> {
  const contract = readObject(join(stateRoot, "contract.json"));
  if (contract.repeat !== repeat) throw new DoctorError("restart repeat drifted");
  const aPath = await resolveArchivePathFromLookup(
    String(contract.a_data_key), stateRoot, "session-a",
  );
  const aArchive = aPath ? await readArchive(aPath) : null;
  const strictWrongSession = await resolveArchivePathFromLookup(
    String(contract.b_data_key), stateRoot, "session-a",
  );
  const bRecovery = await unscopedRecover(String(contract.b_data_key), stateRoot);
  return {
    ...base("verify-restart", repeat),
    restart_preserved_session_a_archive: aArchive?.originalText.includes(String(contract.a_canary)) === true,
    restart_strict_session_lookup_rejected_b: strictWrongSession === null,
    restart_unscoped_mcp_resolver_disclosed_b_to_any_caller: bRecovery.includes(String(contract.b_canary)),
    recovery_api_accepts_session_scope: false,
    status: TERMINAL_STATUS,
  };
}

async function purgeProbe(stateRoot: string, repeat: number): Promise<JsonObject> {
  const contract = readObject(join(stateRoot, "contract.json"));
  if (contract.repeat !== repeat) throw new DoctorError("purge repeat drifted");
  const store = createFileSystemArtifactStore() as unknown as JsonObject;
  const publicMethods = Object.keys(store).sort();
  const files = walkFiles(stateRoot);
  const merged = Buffer.concat(files.map((path) => readFileSync(path)));
  const bRecovery = await unscopedRecover(String(contract.b_data_key), stateRoot);
  return {
    ...base("purge-probe", repeat),
    status: TERMINAL_STATUS,
    native_artifact_store_methods: publicMethods,
    native_scoped_purge_api_available: publicMethods.some((name) => ["delete", "erase", "forget", "purge"].includes(name)),
    plaintext_a_remains: merged.includes(Buffer.from(String(contract.a_canary))),
    plaintext_b_remains: merged.includes(Buffer.from(String(contract.b_canary))),
    other_session_remains_recoverable: bRecovery.includes(String(contract.b_canary)),
    h100_actor_admission: "forbidden-for-this-revision",
  };
}

async function main(): Promise<void> {
  const [phase, ...args] = process.argv.slice(2);
  const rootIndex = args.indexOf("--state-root");
  const repeatIndex = args.indexOf("--repeat");
  if (rootIndex < 0 || repeatIndex < 0) throw new DoctorError("missing required arguments");
  const stateRoot = args[rootIndex + 1] ?? "";
  const repeat = Number(args[repeatIndex + 1]);
  if (!Number.isInteger(repeat) || repeat <= 0) throw new DoctorError("invalid repeat");
  mkdirSync(stateRoot, { recursive: true });
  const result = phase === "prepare"
    ? await prepare(stateRoot, repeat)
    : phase === "verify-restart"
      ? await verifyRestart(stateRoot, repeat)
      : phase === "purge-probe"
        ? await purgeProbe(stateRoot, repeat)
        : (() => { throw new DoctorError(`unknown phase: ${phase}`); })();
  process.stdout.write(canonicalBytes(result));
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.stack ?? error.message : String(error)}\n`);
  process.exitCode = 1;
});
