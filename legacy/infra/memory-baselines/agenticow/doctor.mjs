#!/usr/bin/env node
/** Two-phase exact-source agenticow branch/promotion/erasure falsifier. */

import fs from 'node:fs';
import path from 'node:path';
import { AgenticMemory, open } from '/opt/agenticow/src/index.js';

const state = '/state';
const manifests = {
  base: path.join(state, 'base.json'),
  a: path.join(state, 'a.json'),
  b: path.join(state, 'b.json'),
  nested: path.join(state, 'nested.json'),
};

const vector = (slot) => Float32Array.from({ length: 8 }, (_, i) => i === slot ? 1 : 0);
const ids = (memory, query) => memory.query(query, 16).map((hit) => hit.id);
const textFor = (memory, query, id) => memory.query(query, 16).find((hit) => hit.id === id)?.text;

function phaseOne() {
  fs.mkdirSync(state, { recursive: true });
  const canaries = {
    deleted: process.env.COTCODEC_DELETED_CANARY,
    a: process.env.COTCODEC_A_CANARY,
    b: process.env.COTCODEC_B_CANARY,
    nested: process.env.COTCODEC_NESTED_CANARY,
    childConflict: process.env.COTCODEC_CHILD_CONFLICT_CANARY,
    parentConflict: process.env.COTCODEC_PARENT_CONFLICT_CANARY,
  };
  const base = open(path.join(state, 'base.rvf'), { dimension: 8, metric: 'cosine' });
  base.ingest([
    { id: 10, vector: vector(0), text: 'shared' },
    { id: 20, vector: vector(1), text: canaries.deleted },
    { id: 30, vector: vector(2), text: 'conflict-origin' },
  ]);

  const a = base.branch('tenant-a', path.join(state, 'a.rvf'));
  const b = base.branch('tenant-b', path.join(state, 'b.rvf'));
  a.ingest([{ id: 101, vector: vector(3), text: canaries.a }]);
  b.ingest([{ id: 102, vector: vector(4), text: canaries.b }]);
  const nested = a.branch('tenant-a-nested', path.join(state, 'nested.rvf'));
  nested.ingest([{ id: 103, vector: vector(5), text: canaries.nested }]);

  const checkpoint = a.checkpoint('clean');
  a.ingest([{ id: 666, vector: vector(6), text: 'poison' }]);
  const poisonVisible = ids(a, vector(6)).includes(666);
  a.rollback(checkpoint.id);
  const rollbackRemovedPoison = !ids(a, vector(6)).includes(666);

  a.delete([20]);
  const tombstoneMasksAncestor = !ids(a, vector(1)).includes(20);
  const siblingStillSeesDeleted = ids(b, vector(1)).includes(20);

  a.ingest([{ id: 30, vector: vector(7), text: canaries.childConflict }]);
  base.ingest([{ id: 30, vector: vector(6), text: canaries.parentConflict }]);
  const parentHadLaterUpdate = textFor(base, vector(6), 30) === canaries.parentConflict;
  const firstPromotion = a.promote(base);
  const childBlindlyOverwroteLaterParent =
    textFor(base, vector(7), 30) === canaries.childConflict;
  const epochBeforeRepeat = base.status().epoch;
  const secondPromotion = a.promote(base);
  const epochAfterRepeat = base.status().epoch;
  const repeatedPromotionLogicallyIdempotent =
    firstPromotion.ingested === 1 && secondPromotion.ingested === 1 &&
    epochAfterRepeat === epochBeforeRepeat &&
    textFor(base, vector(7), 30) === canaries.childConflict;

  for (const [name, memory] of Object.entries({ base, a, b, nested })) {
    memory.save(manifests[name]);
  }
  const branchIsolation =
    ids(a, vector(4)).includes(102) === false &&
    ids(b, vector(3)).includes(101) === false;
  const nestedIsolation =
    ids(nested, vector(3)).includes(101) &&
    !ids(a, vector(5)).includes(103) &&
    ids(nested, vector(5)).includes(103);
  for (const memory of [base, a, b, nested]) memory.close();

  return {
    phase: 1,
    branch_isolation: branchIsolation,
    nested_fork_isolation: nestedIsolation,
    checkpoint_poison_visible_before_rollback: poisonVisible,
    checkpoint_rollback_removed_poison: rollbackRemovedPoison,
    tombstone_masks_ancestor: tombstoneMasksAncestor,
    sibling_still_sees_tombstoned_ancestor: siblingStillSeesDeleted,
    parent_later_update_existed_before_promotion: parentHadLaterUpdate,
    promotion_blindly_overwrites_later_parent_update: childBlindlyOverwroteLaterParent,
    repeated_promotion_logically_idempotent: repeatedPromotionLogicallyIdempotent,
    native_scoped_purge_absent: !['purge', 'purgeBranch', 'erase', 'eraseBranch']
      .some((name) => typeof AgenticMemory.prototype[name] === 'function'),
  };
}

function phaseTwo() {
  const deleted = process.env.COTCODEC_DELETED_CANARY;
  const aCanary = process.env.COTCODEC_A_CANARY;
  const bCanary = process.env.COTCODEC_B_CANARY;
  const nestedCanary = process.env.COTCODEC_NESTED_CANARY;
  const childConflict = process.env.COTCODEC_CHILD_CONFLICT_CANARY;
  const memories = Object.fromEntries(
    Object.entries(manifests).map(([name, manifest]) => [name, AgenticMemory.load(manifest)]),
  );
  const checks = {
    branch_isolation_survived_restart:
      !ids(memories.a, vector(4)).includes(102) &&
      !ids(memories.b, vector(3)).includes(101),
    nested_fork_isolation_survived_restart:
      ids(memories.nested, vector(3)).includes(101) &&
      ids(memories.nested, vector(5)).includes(103) &&
      !ids(memories.a, vector(5)).includes(103),
    branch_text_payloads_survived_restart:
      textFor(memories.a, vector(3), 101) === aCanary &&
      textFor(memories.b, vector(4), 102) === bCanary &&
      textFor(memories.nested, vector(5), 103) === nestedCanary,
    tombstone_survived_restart: !ids(memories.a, vector(1)).includes(20),
    sibling_visibility_survived_restart: ids(memories.b, vector(1)).includes(20),
    promoted_child_value_survived_restart:
      textFor(memories.base, vector(7), 30) === childConflict,
    tombstoned_plaintext_survived_restart:
      fs.readFileSync(manifests.a).includes(Buffer.from(deleted)),
  };
  for (const memory of Object.values(memories)) memory.close();
  return { phase: 2, ...checks };
}

const phase = Number(process.env.COTCODEC_PHASE);
const report = phase === 1 ? phaseOne() : phaseTwo();
const values = Object.entries(report).filter(([key]) => key !== 'phase').map(([, value]) => value);
if (values.length === 0 || values.some((value) => value !== true)) {
  throw new Error(`agenticow falsifier check failed: ${JSON.stringify(report)}`);
}
console.log(`COTCODEC_AGENTICOW_PHASE=${JSON.stringify(report)}`);
