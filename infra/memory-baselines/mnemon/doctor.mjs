import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import {
  MnemonService,
  createRunner,
  resolveConfig,
} from '/opt/dsh-mnemon/lib/index.js'

const DATA_ROOT = '/tmp/mnemon-admission'
const MARKER_A = 'COTCODEC_MNEMON_ACTIVE_ALPHA_42'
const MARKER_B = 'COTCODEC_MNEMON_INACTIVE_BRAVO_84'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function makeService() {
  const config = resolveConfig({
    cliPath: '/usr/local/bin/mnemon',
    storageScope: 'custom',
    dataDir: DATA_ROOT,
    writeEnabled: true,
    timeoutMs: 10_000,
    defaultRecallLimit: 10,
  })
  const runner = createRunner(config)
  assert(runner.commandFound, 'pinned Mnemon CLI is not executable')
  return new MnemonService(runner, config)
}

function resultHas(response, marker) {
  return response.results.some(result => result.content.includes(marker))
}

async function run() {
  let service = makeService()
  const alpha = await service.createBody({
    name: 'Alpha',
    description: 'Primary active memory space.',
    active: true,
  })
  const bravo = await service.createBody({
    name: 'Bravo',
    description: 'Initially inactive memory space.',
    active: false,
  })
  assert(alpha.id !== bravo.id, 'memory spaces share an ID')
  assert(alpha.dbPath !== bravo.dbPath, 'memory spaces share a database')

  const alphaWrite = await service.remember({
    content: MARKER_A,
    category: 'fact',
    source: 'user',
    memoryBodyId: alpha.id,
  })
  const bravoWrite = await service.remember({
    content: MARKER_B,
    category: 'fact',
    source: 'user',
    memoryBodyId: bravo.id,
  })
  assert(typeof alphaWrite.id === 'string', 'alpha write did not return an ID')
  assert(typeof bravoWrite.id === 'string', 'bravo write did not return an ID')
  assert(service.memoryBodies.get(bravo.id).active, 'targeted write did not activate bravo')

  service.updateBody(bravo.id, { active: false })
  const activeOnly = await service.search({ query: MARKER_B, mode: 'keyword' })
  assert(!resultHas(activeOnly, MARKER_B), 'inactive space leaked into default recall')

  let inactiveReadRejected = false
  try {
    await service.search({ query: MARKER_B, mode: 'keyword', memoryBodyIds: [bravo.id] })
  } catch (error) {
    inactiveReadRejected = String(error).includes('not active for reading')
  }
  assert(inactiveReadRejected, 'explicit inactive-space read was not rejected')

  const alphaRead = await service.search({ query: MARKER_A, mode: 'keyword' })
  assert(resultHas(alphaRead, MARKER_A), 'active alpha marker was not recalled')

  service = makeService()
  assert(service.memoryBodies.get(alpha.id).active, 'alpha activation did not survive restart')
  assert(!service.memoryBodies.get(bravo.id).active, 'bravo deactivation did not survive restart')
  const afterRestart = await service.search({ query: MARKER_B, mode: 'keyword' })
  assert(!resultHas(afterRestart, MARKER_B), 'restart widened the active read set')

  service.updateBody(bravo.id, { active: true })
  const bravoRead = await service.search({
    query: MARKER_B,
    mode: 'keyword',
    memoryBodyIds: [bravo.id],
  })
  assert(resultHas(bravoRead, MARKER_B), 'reactivated bravo marker was not recalled')

  await service.forget(bravoWrite.id, undefined, bravo.id)
  const afterForget = await service.search({
    query: MARKER_B,
    mode: 'keyword',
    memoryBodyIds: [bravo.id],
  })
  assert(!resultHas(afterForget, MARKER_B), 'soft-forgotten marker remained recallable')
  const databaseBytes = readFileSync(bravo.dbPath)
  const softDeletePreservedPlaintext = databaseBytes.includes(Buffer.from(MARKER_B))
  assert(softDeletePreservedPlaintext, 'soft-delete did not preserve the expected source row')

  await service.deleteBody(bravo.id)
  assert(!existsSync(resolve(bravo.dbPath, '..')), 'deleted memory-space directory remains')
  service = makeService()
  assert(service.memoryBodies.list().length === 1, 'deleted space reappeared after restart')
  assert(service.memoryBodies.get(alpha.id).active, 'remaining active space changed')

  let lastSpaceDeletionRejected = false
  try {
    await service.deleteBody(alpha.id)
  } catch (error) {
    lastSpaceDeletionRejected = String(error).includes('cannot delete the last Mnemon Store')
  }
  assert(lastSpaceDeletionRejected, 'last native store deletion was not rejected')

  const checks = {
    core_named_stores_use_distinct_databases: true,
    plugin_active_set_limits_default_recall: true,
    explicit_inactive_read_is_rejected: true,
    targeted_write_autoactivates_space: true,
    activation_registry_survives_restart: true,
    core_soft_forget_hides_but_preserves_row: true,
    plugin_space_delete_removes_store_directory: true,
    last_native_store_delete_is_rejected: true,
  }
  const report = {
    schema_version: 1,
    system_id: 'mnemon-dsh-static-active-space-admission-v1',
    status: 'ADMITTED_STATIC_ACTIVE_SPACE_CONTROL_WITH_SOFT_DELETE_BOUNDARY',
    scientific_result: false,
    publication_ready: false,
    h100_actor_admission: true,
    checks,
    observations: {
      memory_space_count_before_delete: 2,
      memory_space_count_after_delete: 1,
      active_count_after_restart: 1,
      soft_delete_preserved_plaintext: true,
      active_selection_owner: 'dsh-mnemon-plugin',
      native_store_owner: 'mnemon-core',
      learned_promotion_or_demotion: false,
      access_control: false,
      physical_item_erasure_proven: false,
    },
  }
  process.stdout.write(`COTCODEC_MNEMON_REPORT=${JSON.stringify(report)}\n`)
}

run().catch(error => {
  process.stderr.write(`${error instanceof Error ? error.stack : String(error)}\n`)
  process.exitCode = 1
})
