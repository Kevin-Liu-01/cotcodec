#!/usr/bin/env node
/** Contained lifecycle admission doctor for Mnemosyne Cognitive Memory OS. */

import { createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";
import process from "node:process";

import createMnemosyne from "/opt/mnemosyne/source/dist/index.js";

const EXPECTED_REVISION = "5506aae7cec9ada5523099fd5ab858a4eee593b6";
const EXPECTED_STATUS = "MNEMOSYNE_COGNITIVE_ACTIVE_INACTIVE_ADMISSION_KILLED";
const CANARY = "COTCODEC_MNEMOSYNE_PHYSICAL_ERASURE_CANARY_5506AAE";
const IDS = Object.freeze({
  popular: "00000000-0000-4000-8000-000000000001",
  stale: "00000000-0000-4000-8000-000000000002",
  duplicateKeeper: "00000000-0000-4000-8000-000000000003",
  duplicateLoser: "00000000-0000-4000-8000-000000000004",
  forgotten: "00000000-0000-4000-8000-000000000005",
});

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function sha256(value) {
  return createHash("sha256").update(canonical(value)).digest("hex");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function vector(axis) {
  const value = new Array(768).fill(0);
  value[axis] = 1;
  return value;
}

function parseArgs(argv) {
  const result = { phase: "", output: "" };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--phase") result.phase = argv[++index] ?? "";
    else if (argv[index] === "--output") result.output = argv[++index] ?? "";
    else throw new Error(`unknown argument: ${argv[index]}`);
  }
  assert(["initial", "restart"].includes(result.phase), "--phase must be initial or restart");
  return result;
}

function config() {
  const qdrantUrl = process.env.COTCODEC_QDRANT_URL;
  const collection = process.env.COTCODEC_COLLECTION;
  assert(qdrantUrl, "COTCODEC_QDRANT_URL is required");
  assert(collection && /^[a-z0-9_]{8,63}$/.test(collection), "invalid COTCODEC_COLLECTION");
  return {
    qdrantUrl,
    collection,
    privateCollection: `${collection}_private`,
    profilesCollection: `${collection}_profiles`,
    skillsCollection: `${collection}_skills`,
  };
}

async function instance(runtime) {
  return createMnemosyne({
    qdrantUrl: runtime.qdrantUrl,
    embeddingUrl: "http://disabled.invalid/v1/embeddings",
    agentId: "cotcodec-mnemosyne-doctor",
    enableExtraction: false,
    enableGraph: false,
    enableAutoLink: false,
    enableDecay: false,
    enablePriorityScoring: false,
    enableConfidenceTags: false,
    enableBM25: false,
    enablePreferenceTracking: false,
    enableSentimentTracking: false,
    enableLessonExtraction: false,
    enableTemporalMining: false,
    enableProactiveWarnings: false,
    enableDreamConsolidation: false,
    enableBroadcast: false,
    enableCollectiveSynthesis: false,
    redisUrl: "",
    collections: {
      shared: runtime.collection,
      private: runtime.privateCollection,
      profiles: runtime.profilesCollection,
      skills: runtime.skillsCollection,
    },
  });
}

async function rawPoint(runtime, id) {
  const response = await fetch(`${runtime.qdrantUrl}/collections/${runtime.collection}/points/${id}`);
  assert(response.ok, `point ${id} unavailable: ${response.status}`);
  const data = await response.json();
  return data.result;
}

async function seed(db, runtime) {
  const oldIso = "2025-01-01T00:00:00.000Z";
  const oldAccess = Date.parse(oldIso);
  const common = {
    classification: "public",
    scope: "public",
    urgency: "reference",
    domain: "knowledge",
    confidence: 0.8,
    confidenceTag: "grounded",
    linkedMemories: [],
    eventTime: oldIso,
    ingestedAt: oldIso,
    createdAt: oldIso,
    accessTimes: [oldAccess],
  };
  await db.store("popular episodic source", vector(0), {
    ...common,
    id: IDS.popular,
    memoryType: "episodic",
    accessCount: 11,
    priorityScore: 0.8,
    importance: 0.8,
  });
  await db.store("stale low-importance source", vector(1), {
    ...common,
    id: IDS.stale,
    memoryType: "semantic",
    accessCount: 0,
    priorityScore: 0.8,
    importance: 0.2,
  });
  await db.store("duplicate source alpha", vector(2), {
    ...common,
    id: IDS.duplicateKeeper,
    memoryType: "episodic",
    accessCount: 5,
    priorityScore: 0.5,
    importance: 0.7,
    metadata: { source_event_id: "event-duplicate-a" },
  });
  await db.store("duplicate source beta", vector(2), {
    ...common,
    id: IDS.duplicateLoser,
    memoryType: "episodic",
    accessCount: 1,
    priorityScore: 0.5,
    importance: 0.7,
    metadata: { source_event_id: "event-duplicate-b" },
  });
  await db.store(CANARY, vector(3), {
    ...common,
    id: IDS.forgotten,
    memoryType: "semantic",
    accessCount: 2,
    priorityScore: 0.7,
    importance: 0.9,
    metadata: { source_event_id: "event-forget-canary" },
  });
  assert(await db.count(runtime.collection) === 5, "seed point count drifted");
}

async function initial(runtime) {
  const memory = await instance(runtime);
  assert(await memory.db.count(runtime.collection) === 0, "collection was not empty");
  await seed(memory.db, runtime);

  const first = await memory.consolidate({ dryRun: true });
  const staleAfterFirst = await rawPoint(runtime, IDS.stale);
  const second = await memory.consolidate();
  const staleAfterSecond = await rawPoint(runtime, IDS.stale);
  const popular = await rawPoint(runtime, IDS.popular);
  const duplicateLoser = await rawPoint(runtime, IDS.duplicateLoser);
  const staleSearch = await memory.db.search(runtime.collection, vector(1), 5, 0.1);

  const forgot = await memory.forget(IDS.forgotten);
  const forgotten = await rawPoint(runtime, IDS.forgotten);
  const forgottenSearch = await memory.db.search(runtime.collection, vector(3), 5, 0.1);

  const checks = {
    public_forget_reported_success: forgot === true,
    forgotten_hidden_from_search: !forgottenSearch.some((result) => result.entry.id === IDS.forgotten),
    forgotten_point_physically_resident: forgotten.payload?.deleted === true && forgotten.payload?.text === CANARY,
    duplicate_soft_deleted: duplicateLoser.payload?.deleted === true,
    popular_promoted_to_core: popular.payload?.memory_type === "core",
    dry_run_mutated_stale_priority: staleAfterFirst.payload?.priority_score === 0.4,
    repeated_consolidation_halved_again: staleAfterSecond.payload?.priority_score === 0.2,
    repeated_consolidation_non_idempotent: first.staleDemoted === 1 && second.staleDemoted === 1,
    demoted_memory_remains_in_serving_search: staleSearch.some((result) => result.entry.id === IDS.stale),
    analyzed_count_is_batch_cap_not_resident_count: first.analyzed === 200 && await memory.db.count(runtime.collection) === 5,
    no_native_scoped_purge: typeof memory.purge !== "function",
  };
  assert(Object.values(checks).every(Boolean), `initial lifecycle semantics drifted: ${canonical(checks)}`);
  return { checks, firstReport: first, secondReport: second };
}

async function restart(runtime) {
  const memory = await instance(runtime);
  const stale = await rawPoint(runtime, IDS.stale);
  const popular = await rawPoint(runtime, IDS.popular);
  const duplicateLoser = await rawPoint(runtime, IDS.duplicateLoser);
  const forgotten = await rawPoint(runtime, IDS.forgotten);
  const forgottenSearch = await memory.db.search(runtime.collection, vector(3), 5, 0.1);
  const checks = {
    five_points_persist_after_fresh_database_process: await memory.db.count(runtime.collection) === 5,
    promoted_core_persists: popular.payload?.memory_type === "core",
    repeated_demotion_persists: stale.payload?.priority_score === 0.2,
    duplicate_tombstone_persists: duplicateLoser.payload?.deleted === true,
    forgotten_tombstone_persists: forgotten.payload?.deleted === true,
    forgotten_plaintext_persists: forgotten.payload?.text === CANARY,
    forgotten_remains_hidden_from_search: !forgottenSearch.some((result) => result.entry.id === IDS.forgotten),
    no_native_scoped_purge_after_restart: typeof memory.purge !== "function",
  };
  assert(Object.values(checks).every(Boolean), `restart lifecycle semantics drifted: ${canonical(checks)}`);
  return { checks };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const runtime = config();
  const projection = args.phase === "initial" ? await initial(runtime) : await restart(runtime);
  const report = {
    schema_version: 1,
    source_revision: EXPECTED_REVISION,
    phase: args.phase,
    status: EXPECTED_STATUS,
    scientific_result: false,
    publication_ready: false,
    h100_actor_admission: false,
    provider_calls: 0,
    model_backend_calls: 0,
    projection,
    projection_sha256: sha256(projection),
  };
  const encoded = `${JSON.stringify(report, null, 2)}\n`;
  if (args.output) await writeFile(args.output, encoded, { encoding: "utf8", flag: "wx" });
  else process.stdout.write(encoded);
}

main().catch((error) => {
  process.stderr.write(`${error.stack ?? error}\n`);
  process.exitCode = 1;
});
