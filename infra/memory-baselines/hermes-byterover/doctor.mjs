import {createHash} from 'node:crypto'
import {mkdirSync, readFileSync, readdirSync, writeFileSync} from 'node:fs'
import {join} from 'node:path'
import {spawnSync} from 'node:child_process'

const phase = process.argv[2]
const state = process.env.COTCODEC_STATE_ROOT
if (!state || !['prepare', 'restart'].includes(phase)) {
  throw new Error('usage: doctor.mjs <prepare|restart> with COTCODEC_STATE_ROOT')
}

const project = join(state, 'project')
const tree = join(project, '.brv', 'context-tree', 'project')
mkdirSync(tree, {recursive: true})
mkdirSync(process.env.HOME, {recursive: true})
mkdirSync(process.env.BRV_DATA_DIR, {recursive: true})

const canary = 'BYTEROVER_ZEPHYR_7F1D9A'
const contextPath = join(tree, 'zephyr.md')
if (phase === 'prepare') {
  writeFileSync(
    contextPath,
    `---\ntitle: Project Zephyr\ntags: [project]\n---\n\n${canary} Alice owns Project Zephyr.\n`,
    {flag: 'wx'},
  )
}

function run(args, timeout = 7_000) {
  const result = spawnSync('brv', args, {
    cwd: project,
    encoding: 'utf8',
    env: {...process.env, BRV_ENV: 'production'},
    timeout,
  })
  return {
    args,
    exit_code: result.status,
    signal: result.signal,
    stdout: (result.stdout ?? '').trim(),
    stderr: (result.stderr ?? '').trim(),
    timed_out: result.error?.code === 'ETIMEDOUT',
  }
}

const version = run(['--version'])
const search = run(['search', 'Who owns Project Zephyr?', '--format', 'json'])
const hermesQuery = run(['query', '--', 'Who owns Project Zephyr?'])
const hermesCurate = run(['curate', '--', `${canary} Alice owns Project Zephyr`])

const logDir = join(process.env.BRV_DATA_DIR, 'logs')
const daemonLogs = readdirSync(logDir, {withFileTypes: true})
  .filter((entry) => entry.isFile() && entry.name.endsWith('.log'))
  .map((entry) => readFileSync(join(logDir, entry.name), 'utf8'))
const fatalNetworkCount = daemonLogs.filter((content) =>
  content.includes('Fatal startup error: ❌ Network error'),
).length

const adapterSource = readFileSync('/opt/doctor/hermes-byterover.py', 'utf8')
const sourceChecks = {
  query_uses_llm_command: adapterSource.includes('["query", "--", query.strip()[:5000]]'),
  curate_uses_llm_command: adapterSource.includes('["curate", "--", content]'),
  profile_directory_ignores_session_id:
    adapterSource.includes('return get_hermes_home() / "byterover"') &&
    !adapterSource.includes('get_hermes_home() / "byterover" / self._session_id'),
  no_provider_purge_method: !adapterSource.includes('def purge('),
}

const result = {
  schema_version: 1,
  phase,
  canary,
  canary_file_sha256: createHash('sha256').update(readFileSync(contextPath)).digest('hex'),
  version,
  offline_search: search,
  hermes_query: hermesQuery,
  hermes_curate: hermesCurate,
  daemon: {
    log_count: daemonLogs.length,
    fatal_network_count: fatalNetworkCount,
    every_log_has_network_fatal:
      daemonLogs.length > 0 && fatalNetworkCount === daemonLogs.length,
  },
  source_checks: sourceChecks,
}

process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)
