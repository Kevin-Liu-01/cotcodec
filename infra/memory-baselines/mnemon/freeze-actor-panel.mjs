import { rmSync } from 'node:fs'

import {
  MnemonService,
  createRunner,
  resolveConfig,
} from '/opt/dsh-mnemon/lib/index.js'

const DATA_ROOT = '/tmp/mnemon-actor-freeze'
const SPACE_NAMES = ['ALPHA', 'BRAVO', 'CHARLIE', 'DELTA']
const TASK_COUNT = 32
const TOP_K = 4

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function makeService(dataRoot) {
  const config = resolveConfig({
    cliPath: '/usr/local/bin/mnemon',
    storageScope: 'custom',
    dataDir: dataRoot,
    writeEnabled: true,
    timeoutMs: 10_000,
    defaultRecallLimit: TOP_K,
  })
  const runner = createRunner(config)
  assert(runner.commandFound, 'pinned Mnemon CLI is not executable')
  return new MnemonService(runner, config)
}

function codeFor(spaceIndex, taskIndex) {
  const suffix = 700 + spaceIndex * 53 + taskIndex * 7
  return `${SPACE_NAMES[spaceIndex]}-${String(taskIndex).padStart(2, '0')}-${suffix}`
}

function recordFor(spaceIndex, taskIndex) {
  const space = SPACE_NAMES[spaceIndex]
  return `Workspace ${space} record entity-${String(taskIndex).padStart(2, '0')} states access-code ${codeFor(spaceIndex, taskIndex)}. This is the authoritative current assignment.`
}

function setOnlyActive(service, bodyBySpace, selectedSpace) {
  for (const space of SPACE_NAMES) {
    service.updateBody(bodyBySpace.get(space).id, { active: space === selectedSpace })
  }
}

function setAllActive(service, bodyBySpace) {
  for (const space of SPACE_NAMES) {
    service.updateBody(bodyBySpace.get(space).id, { active: true })
  }
}

function slots(response, bodyNameById) {
  return response.results.map(result => ({
    text: result.content,
    source_space: bodyNameById.get(result.memoryBodyId),
    is_padding: false,
  }))
}

function padSlots(values, selectedSpace) {
  const padded = [...values]
  while (padded.length < TOP_K) {
    padded.push({
      text: `Workspace ${selectedSpace} contains no additional matching authoritative record for this request.`,
      source_space: null,
      is_padding: true,
    })
  }
  return padded
}

async function run() {
  rmSync(DATA_ROOT, { recursive: true, force: true })
  const items = []
  for (let taskIndex = 0; taskIndex < TASK_COUNT; taskIndex += 1) {
    const service = makeService(`${DATA_ROOT}/task-${String(taskIndex).padStart(3, '0')}`)
    const bodyBySpace = new Map()
    const bodyNameById = new Map()
    for (const [spaceIndex, space] of SPACE_NAMES.entries()) {
      const body = await service.createBody({
        name: space,
        description: `Static task-blind ${space} memory space.`,
        active: spaceIndex === 0,
      })
      bodyBySpace.set(space, body)
      bodyNameById.set(body.id, space)
      await service.remember({
        content: recordFor(spaceIndex, taskIndex),
        category: 'fact',
        source: 'user',
        memoryBodyId: body.id,
      })
    }

    const spaceIndex = (taskIndex * 3 + 1) % SPACE_NAMES.length
    const targetSpace = SPACE_NAMES[spaceIndex]
    const question = `In Workspace ${targetSpace}, what access-code is assigned to entity-${String(taskIndex).padStart(2, '0')}?`

    setAllActive(service, bodyBySpace)
    const allSpaces = slots(await service.search({
      query: question,
      mode: 'keyword',
      limit: TOP_K,
    }), bodyNameById)

    const selectedSpace = SPACE_NAMES.find(space => question.includes(`Workspace ${space}`))
    assert(selectedSpace === targetSpace, 'task-blind lexical router missed an explicit workspace cue')
    setOnlyActive(service, bodyBySpace, selectedSpace)
    const lexical = padSlots(slots(await service.search({
      query: question,
      mode: 'keyword',
      limit: TOP_K,
    }), bodyNameById), selectedSpace)

    setOnlyActive(service, bodyBySpace, targetSpace)
    const oracle = padSlots(slots(await service.search({
      query: question,
      mode: 'keyword',
      limit: TOP_K,
    }), bodyNameById), targetSpace)

    const targetRecord = recordFor(spaceIndex, taskIndex)
    assert(allSpaces.length === TOP_K, 'all-spaces retrieval did not return all four native stores')
    assert(lexical.length === TOP_K, 'routed retrieval did not compile four fixed context slots')
    assert(oracle.length === TOP_K, 'oracle retrieval did not compile four fixed context slots')
    assert(allSpaces.some(slot => slot.text === targetRecord), 'all-spaces retrieval omitted the target record')
    assert(lexical.some(slot => slot.text === targetRecord), 'lexical routed retrieval omitted the target record')
    assert(JSON.stringify(lexical) === JSON.stringify(oracle), 'lexical and oracle contexts differ')
    assert(lexical.filter(slot => !slot.is_padding).every(slot => slot.source_space === targetSpace), 'inactive-space evidence leaked into routed context')

    items.push({
      task_id: `mnemon-static-${String(taskIndex).padStart(3, '0')}`,
      group_id: `entity-${String(taskIndex).padStart(2, '0')}`,
      question,
      answer: codeFor(spaceIndex, taskIndex),
      target_space: targetSpace,
      routed_space: selectedSpace,
      arms: {
        no_memory: [],
        all_spaces: allSpaces,
        lexical_router: lexical,
        oracle_space: oracle,
      },
    })
  }

  const panel = {
    schema_version: 1,
    study: 'mnemon-static-space-h100-actor-v1',
    source_id: 'mnemon',
    source_revisions: {
      'https://github.com/mnemon-dev/mnemon': '88d2981edeb18a5ebe048af472f6f96527615454',
      'https://github.com/omdsh-dev/dsh-mnemon': '1889c68400e52a391ee9a6eedf15bf44bc39dd06',
    },
    active_selection_owner: 'dsh-mnemon-plugin',
    retrieval_owner: 'mnemon-core',
    task_count: items.length,
    group_count: items.length,
    arms: ['no_memory', 'all_spaces', 'lexical_router', 'oracle_space'],
    retrieval_top_k: TOP_K,
    fixed_slot_characters: 160,
    retrieval_calls_per_nonempty_arm: 1,
    router_inputs: ['question'],
    answer_labels_available_to_router: false,
    padding_is_memory_evidence: false,
    scientific_result: false,
    publication_ready: false,
    items,
  }
  process.stdout.write(`COTCODEC_MNEMON_ACTOR_PANEL=${JSON.stringify(panel)}\n`)
}

run().catch(error => {
  process.stderr.write(`${error instanceof Error ? error.stack : String(error)}\n`)
  process.exitCode = 1
})
