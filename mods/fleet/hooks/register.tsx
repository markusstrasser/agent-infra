import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Row } from '../types'

// Replaces pgrep + log peeks: subagents ($.agent.list), the background tasks
// the last Stop event reported, bgrun jobs (<TMPDIR>/bgrun: .pid/.done
// markers) and lanes that are not DONE (`lane ls`). Polls only while open.

const rows = atom({ plugin: 'fleet', key: 'rows' } as const, [])
const tasks = atom({ plugin: 'fleet', key: 'tasks' } as const, [])
const refreshedAt = atom({ plugin: 'fleet', key: 'refreshedAt' } as const, 0)
const error = atom({ plugin: 'fleet', key: 'error' } as const, '')

const PANE = 'fleet'
const POLL_MS = 15_000
const LIVE_AGENT = new Set(['pending', 'running', 'waiting'])

type $ = EngineInterface

const age = (ms: number) => (ms < 120_000 ? `${Math.round(ms / 1000)}s` : ms < 7_200_000 ? `${Math.round(ms / 60_000)}m` : `${Math.round(ms / 3_600_000)}h`)

export function parseLanes(out: string): Row[] {
  return out
    .split('\n')
    .slice(1)
    .map(l => l.trim().split(/\s+/))
    .filter(f => f.length >= 2 && f[0] !== '' && !(f[1] ?? '').startsWith('DONE'))
    .map(f => ({ kind: 'lane' as const, name: f[0]!, state: f[1]!, detail: `log ${f[2] ?? '?'}`, isLive: true }))
}

async function bgrunRows($: $, now: number): Promise<Row[]> {
  const dir = (await $.env.get('BGRUN_DIR')) ?? `${((await $.env.get('TMPDIR')) ?? '/tmp').replace(/\/$/, '')}/bgrun`
  if (!(await $.fs.exists(dir))) return []
  const entries = await $.fs.list(dir)
  const names = entries.filter(f => f.name.endsWith('.pid')).map(f => f.name.slice(0, -4))
  const out: Row[] = []
  for (const name of names) {
    const done = entries.find(f => f.name === `${name}.done`)
    const log = entries.find(f => f.name === `${name}.log`)
    const rc = done ? (await $.fs.read(`${dir}/${name}.done`)).trim() : ''
    if (done && now - done.mtimeMs > 6 * 3_600_000) continue
    out.push({
      kind: 'bgrun',
      name,
      state: done ? `rc ${rc}` : 'running',
      detail: log ? `log quiet ${age(now - log.mtimeMs)}` : 'no log',
      isLive: !done,
    })
  }
  return out
}

async function refresh($: $): Promise<void> {
  const now = await $.clock.now()
  const problems: string[] = []
  const agents: Row[] = (await $.agent.list()).map(a => ({
    kind: 'agent',
    name: a.name ?? a.type,
    state: a.status,
    detail: a.description.slice(0, 80),
    isLive: LIVE_AGENT.has(a.status),
  }))
  const bg = await bgrunRows($, now).catch(err => (problems.push(`bgrun: ${String(err).slice(0, 80)}`), [] as Row[]))
  const home = (await $.env.get('HOME')) ?? '/Users/alien'
  const lane = await $.process.run([`${home}/Projects/skills/bin/lane`, 'ls'], { timeoutMs: 20_000 })
  if (lane.exitCode !== 0) problems.push(`lane ls exit ${lane.exitCode}`)
  await update($, rows, () => [...agents, ...bg, ...(lane.exitCode === 0 ? parseLanes(lane.stdout) : [])])
  await update($, refreshedAt, () => now)
  await update($, error, () => problems.join(' · '))
}

let timer: { cancel: () => void } | null = null

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'fleet', description: 'Pane: subagents, background tasks, bgrun jobs, live lanes' })
    return next(e)
  })

  on('command.run', { command: 'fleet' }, async $ => {
    await refresh($)
    await $.ui.open({ id: PANE, title: 'Fleet' })
    timer?.cancel()
    timer = $.clock.every(POLL_MS, () => void refresh($))
    return { text: 'Fleet pane opened.' }
  })

  on('ui.close', { id: PANE }, async ($, e, next) => {
    timer?.cancel()
    timer = null
    return next(e)
  })

  on('classic.Stop', async ($, e, next) => {
    const list = (e.background_tasks ?? []).map(t => ({
      kind: 'task' as const,
      name: t.name ?? t.agent_type ?? t.type,
      state: t.status,
      detail: (t.description || t.command || '').slice(0, 80),
      isLive: true,
    }))
    await update($, tasks, () => list)
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const all = [...(await read($, rows)), ...(await read($, tasks))]
    const err = await read($, error)
    const at = await read($, refreshedAt)
    const live = all.filter(r => r.isLive)
    const quiet = all.filter(r => !r.isLive)
    const line = (r: Row) => (
      <Text key={`${r.kind}-${r.name}`} dimColor={!r.isLive}>
        {r.kind.padEnd(6)} {r.name.slice(0, 28).padEnd(28)} {r.state.padEnd(10)} {r.detail}
      </Text>
    )
    return (
      <Box flexDirection="column">
        {err !== '' && <Text color="warning">[DEGRADED] {err}</Text>}
        <Text dimColor>
          {live.length} live · {quiet.length} finished · refreshed {at ? new Date(at).toISOString().slice(11, 19) : 'never'}Z
        </Text>
        {all.length === 0 && <Text dimColor>Nothing running.</Text>}
        {live.map(line)}
        {quiet.slice(-12).map(line)}
        <Button key="refresh" label="refresh" onPress={() => void refresh($)} />
      </Box>
    )
  })
}
