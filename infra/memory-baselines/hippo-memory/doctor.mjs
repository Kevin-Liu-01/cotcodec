#!/usr/bin/env node
/** Falsification-first doctor for Hippo Memory v1.30.0. */

import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import {
  Layer,
  calculateStrength,
  createMemory,
  deleteEntry,
  loadAllEntries,
  loadRecallSearchEntries,
  markRetrieved,
  readEntry,
  wmClear,
  wmFlush,
  wmPush,
  wmRead,
  writeEntry,
} from '/opt/hippo/dist/index.js';
import { outcome } from '/opt/hippo/dist/api.js';
import { consolidate } from '/opt/hippo/dist/consolidate.js';

const STATE_ROOT = '/state/hippo';
const T0 = '2026-08-14T12:00:00.000Z';
const T10 = '2026-08-24T12:00:00.000Z';
// Far enough after the retrieval clock reset that the 1.1 retrieval boost no
// longer clamps both outcome arms at 1.0.
const T20 = '2026-12-02T12:00:00.000Z';
const FORBIDDEN_SECRET_NAMES = [
  'ANTHROPIC_API_KEY',
  'OPENAI_API_KEY',
  'VOYAGE_API_KEY',
  'COHERE_API_KEY',
];
const CANARIES = [
  'tenant-a-canary-quartz',
  'tenant-b-canary-cobalt',
  'tenant-b-canary-umber',
  'wm-high-canary-cedar',
  'retention-canary-saffron',
];

function fail(message) {
  throw new Error(message);
}

function sha256(value) {
  const bytes = typeof value === 'string' ? Buffer.from(value) : value;
  return createHash('sha256').update(bytes).digest('hex');
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, child]) => [key, canonical(child)]),
    );
  }
  return value;
}

function digest(value) {
  return sha256(JSON.stringify(canonical(value)));
}

function assertNoProviderSecrets() {
  const present = FORBIDDEN_SECRET_NAMES.filter((name) => process.env[name]);
  if (present.length > 0) fail(`provider secrets are forbidden: ${present.join(',')}`);
}

function configPayload() {
  return {
    ambient: { enabled: false },
    autoLearnOnSleep: false,
    autoShareOnSleep: false,
    autoSleep: { enabled: false, threshold: 50 },
    autoTraceCapture: false,
    embeddings: { enabled: false, model: 'disabled', provider: 'local' },
    extraction: { enabled: false, model: 'disabled' },
    global: { enabled: false },
    memoryValue: { enabled: false },
    multihop: { enabled: false },
    physics: { enabled: false },
    replay: { count: 0 },
  };
}

function makeMemory({ id, content, tenantId, sourceEventId, confidence = 'verified' }) {
  process.env.HIPPO_FAKE_NOW = T0;
  const entry = createMemory(content, {
    layer: Layer.Episodic,
    tenantId,
    confidence,
    baseHalfLifeDays: 100,
    source: 'cotcodec-hippo-doctor',
    source_session_id: `session-${tenantId}`,
    artifact_ref: sourceEventId,
    tags: ['cotcodec-doctor', sourceEventId],
  });
  entry.id = id;
  return entry;
}

function stableStateProjection() {
  const rows = loadAllEntries(STATE_ROOT);
  const semantic = rows.filter((entry) => entry.layer === Layer.Semantic);
  const retention = readEntry(STATE_ROOT, 'retention-target', 'tenant-a');
  if (!retention) fail('retention target is missing');
  const wmA = wmRead(STATE_ROOT, { scope: 'scope-a', limit: 100 });
  const wmB = wmRead(STATE_ROOT, { scope: 'scope-b', limit: 100 });
  const semanticProjection = semantic.map((entry) => ({
    tenantId: entry.tenantId,
    layer: entry.layer,
    content: entry.content,
    parents: entry.parents,
    extracted_from: entry.extracted_from,
    artifact_ref: entry.artifact_ref,
    source_session_id: entry.source_session_id,
  }));
  return {
    row_count: rows.length,
    source_tenants: rows
      .filter((entry) => entry.layer === Layer.Episodic)
      .map((entry) => [entry.id, entry.tenantId])
      .sort((a, b) => a[0].localeCompare(b[0])),
    semantic: semanticProjection,
    wm: {
      scope_a_count: wmA.length,
      scope_a_high_present: wmA.some((item) => item.content === CANARIES[3]),
      scope_b_count: wmB.length,
    },
    retention: {
      id: retention.id,
      tenantId: retention.tenantId,
      retrieval_count: retention.retrieval_count,
      half_life_days: retention.half_life_days,
      confidence: retention.confidence,
      outcome_positive: retention.outcome_positive,
      outcome_negative: retention.outcome_negative,
      artifact_ref: retention.artifact_ref,
      source_session_id: retention.source_session_id,
    },
  };
}

async function prepare() {
  if (fs.existsSync(STATE_ROOT) && fs.readdirSync(STATE_ROOT).length > 0) {
    fail('prepare requires an empty state root');
  }
  fs.mkdirSync(STATE_ROOT, { recursive: true, mode: 0o700 });
  fs.writeFileSync(
    path.join(STATE_ROOT, 'config.json'),
    `${JSON.stringify(configPayload(), null, 2)}\n`,
    { flag: 'wx', mode: 0o600 },
  );

  for (let index = 0; index < 21; index += 1) {
    wmPush(STATE_ROOT, {
      scope: 'scope-a',
      sessionId: 'session-a',
      content: `wm-low-${index.toString().padStart(2, '0')}`,
      importance: 0.1,
      metadata: { source_event_id: `wm-event-${index}` },
    });
  }
  wmPush(STATE_ROOT, {
    scope: 'scope-a',
    sessionId: 'session-a',
    content: CANARIES[3],
    importance: 0.9,
    metadata: { source_event_id: 'wm-high-event' },
  });
  wmPush(STATE_ROOT, {
    scope: 'scope-b',
    sessionId: 'session-b',
    content: 'scope-b-isolation-marker',
    importance: 0.5,
    metadata: { source_event_id: 'wm-b-event' },
  });

  const memories = [
    makeMemory({
      id: 'tenant-a-memory',
      tenantId: 'tenant-a',
      sourceEventId: 'event-a',
      content: `shared project alpha timeline ${CANARIES[0]}`,
    }),
    makeMemory({
      id: 'tenant-b-memory-1',
      tenantId: 'tenant-b',
      sourceEventId: 'event-b1',
      content: `shared project alpha timeline ${CANARIES[1]}`,
    }),
    makeMemory({
      id: 'tenant-b-memory-2',
      tenantId: 'tenant-b',
      sourceEventId: 'event-b2',
      content: `shared project alpha timeline ${CANARIES[2]}`,
    }),
    makeMemory({
      id: 'retention-target',
      tenantId: 'tenant-a',
      sourceEventId: 'event-retention',
      confidence: 'stale',
      content: `isolated retention signal ${CANARIES[4]}`,
    }),
  ];
  for (const entry of memories) writeEntry(STATE_ROOT, entry, { actor: 'cotcodec-doctor' });

  const sleep = await consolidate(STATE_ROOT, { now: new Date(T0) });
  if (sleep.replayed !== 0 || sleep.extracted !== 0 || sleep.physicsSimulated !== 0) {
    fail('sleep activated a forbidden coupled mechanism');
  }
  if (sleep.semanticCreated !== 1 || sleep.merged !== 3) {
    fail(`unexpected consolidation result: ${JSON.stringify(sleep)}`);
  }

  const beforeRetrieved = readEntry(STATE_ROOT, 'retention-target', 'tenant-a');
  if (!beforeRetrieved) fail('retention target disappeared during sleep');
  const [strengthened] = markRetrieved([beforeRetrieved], new Date(T10));
  writeEntry(STATE_ROOT, strengthened, { actor: 'cotcodec-doctor' });
  const context = {
    hippoRoot: STATE_ROOT,
    tenantId: 'tenant-a',
    actor: { subject: 'cotcodec-doctor', role: 'admin' },
  };
  const outcomeResult = outcome(context, ['retention-target'], true);
  if (outcomeResult.applied !== 1) fail('positive outcome was not applied');
  const retained = readEntry(STATE_ROOT, 'retention-target', 'tenant-a');
  if (!retained) fail('retention target missing after feedback');
  const withoutOutcome = { ...retained, outcome_score: null, outcome_positive: 0 };
  const withOutcomeStrength = calculateStrength(retained, new Date(T20));
  const withoutOutcomeStrength = calculateStrength(withoutOutcome, new Date(T20));
  if (!(withOutcomeStrength > withoutOutcomeStrength)) {
    fail('positive outcome did not extend effective retention');
  }

  const projection = stableStateProjection();
  const semantic = projection.semantic[0];
  if (!semantic || semantic.tenantId !== 'default') fail('cross-tenant semantic not default-owned');
  if (!CANARIES.slice(0, 3).every((canary) => semantic.content.includes(canary))) {
    fail('cross-tenant semantic did not contain every tenant canary');
  }
  const defaultRecall = loadRecallSearchEntries(
    STATE_ROOT,
    'shared project alpha timeline',
    10,
    'default',
  );
  if (!defaultRecall.some((entry) => entry.layer === Layer.Semantic)) {
    fail('default tenant cannot retrieve the mixed semantic record');
  }
  if (readEntry(STATE_ROOT, 'tenant-b-memory-1', 'tenant-a') !== null) {
    fail('tenant-scoped direct read leaked a source record');
  }

  return {
    phase: 'prepare',
    source_claim: 'fixed-retention-and-consolidation-control-only',
    forbidden_capabilities: {
      active_inactive_paging: true,
      configurable_active_slots: true,
      working_memory_flush_to_archive: true,
    },
    sleep: {
      merged: sleep.merged,
      semantic_created: sleep.semanticCreated,
      replayed: sleep.replayed,
      extracted: sleep.extracted,
      physics_simulated: sleep.physicsSimulated,
    },
    cross_tenant: {
      mixed_semantic_created: true,
      mixed_semantic_tenant_id: semantic.tenantId,
      every_canary_present: true,
      default_tenant_retrievable: true,
      source_lineage_complete: false,
    },
    retention: {
      with_outcome_strength: withOutcomeStrength,
      without_outcome_strength: withoutOutcomeStrength,
      positive_outcome_extends_retention: true,
    },
    projection,
    projection_sha256: digest(projection),
  };
}

function restart() {
  const projection = stableStateProjection();
  const semantic = projection.semantic[0];
  if (!semantic || semantic.tenantId !== 'default') fail('mixed semantic missing after restart');
  if (!CANARIES.slice(0, 3).every((canary) => semantic.content.includes(canary))) {
    fail('mixed semantic content changed after restart');
  }
  return {
    phase: 'restart',
    cross_tenant_semantic_persisted: true,
    projection,
    projection_sha256: digest(projection),
  };
}

function walkFiles(root) {
  const files = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const child = path.join(root, entry.name);
    if (entry.isDirectory()) files.push(...walkFiles(child));
    else if (entry.isFile()) files.push(child);
  }
  return files;
}

function purge() {
  const flushed = wmFlush(STATE_ROOT, { sessionId: 'session-a' });
  const scopeAAfterFlush = wmRead(STATE_ROOT, { scope: 'scope-a', limit: 100 });
  const scopeBAfterFlush = wmRead(STATE_ROOT, { scope: 'scope-b', limit: 100 });
  if (flushed !== 20 || scopeAAfterFlush.length !== 0 || scopeBAfterFlush.length !== 1) {
    fail('working-memory flush did not preserve scope isolation');
  }
  if (loadAllEntries(STATE_ROOT).some((entry) => entry.content.includes(CANARIES[3]))) {
    fail('working-memory flush unexpectedly archived the high-priority entry');
  }

  const rows = loadAllEntries(STATE_ROOT);
  for (const entry of rows) deleteEntry(STATE_ROOT, entry.id, { actor: 'cotcodec-doctor' });
  wmClear(STATE_ROOT);
  const logicalRows = loadAllEntries(STATE_ROOT);
  if (logicalRows.length !== 0 || wmRead(STATE_ROOT, { limit: 100 }).length !== 0) {
    fail('logical purge left live records');
  }

  const physicalHits = [];
  for (const file of walkFiles(STATE_ROOT)) {
    const bytes = fs.readFileSync(file);
    for (const canary of CANARIES) {
      if (bytes.includes(Buffer.from(canary))) {
        physicalHits.push({ file: path.relative(STATE_ROOT, file), canary_sha256: sha256(canary) });
      }
    }
  }
  if (physicalHits.length === 0) fail('expected SQLite plaintext residue was not reproduced');
  if (!physicalHits.some((hit) => hit.file === 'hippo.db')) {
    fail('plaintext residue was not located in hippo.db');
  }
  return {
    phase: 'purge',
    working_memory_flush_count: flushed,
    working_memory_flush_archived: false,
    logical_record_count: logicalRows.length,
    native_scoped_purge_available: false,
    plaintext_residue_reproduced: true,
    physical_hits: physicalHits.sort((a, b) =>
      `${a.file}:${a.canary_sha256}`.localeCompare(`${b.file}:${b.canary_sha256}`),
    ),
  };
}

async function main() {
  assertNoProviderSecrets();
  const phase = process.argv[2];
  let result;
  if (phase === 'prepare') result = await prepare();
  else if (phase === 'restart') result = restart();
  else if (phase === 'purge') result = purge();
  else fail('usage: doctor.mjs <prepare|restart|purge>');
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

await main();
