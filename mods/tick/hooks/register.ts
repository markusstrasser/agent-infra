import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Job } from '../types'

// Wakes this session from inside the process: $.clock + $.prompt.submit.
// Unlike ScheduleWakeup/CronCreate it spends none of the ~15 routines/24h
// account quota, and it dies with the process (no cloud, no resume).

const jobs = atom({ plugin: 'tick', key: 'jobs' } as const, [])
const seq = atom({ plugin: 'tick', key: 'seq' } as const, 0)

const POLL_MS = 15_000
const MIN_MS = 60_000
const MAX_RECURRING_FIRES = 48

type $ = EngineInterface

export function parseDuration(s: string): number | null {
  const m = /^(\d+(?:\.\d+)?)(s|m|h)$/.exec(s.trim())
  if (!m) return null
  const unit = { s: 1_000, m: 60_000, h: 3_600_000 }[m[2] as 's' | 'm' | 'h']
  return Math.round(Number(m[1]) * unit)
}

const fmt = (ms: number) => (ms >= 3_600_000 ? `${(ms / 3_600_000).toFixed(1)}h` : `${Math.max(0, Math.round(ms / 60_000))}m`)

async function schedule($: $, prompt: string, afterMs: number, every: boolean): Promise<Job> {
  const id = `t${await update($, seq, n => n + 1)}`
  const job: Job = {
    id,
    prompt,
    everyMs: every ? afterMs : null,
    dueAt: (await $.clock.now()) + afterMs,
    fired: 0,
    maxFires: every ? MAX_RECURRING_FIRES : 1,
  }
  await update($, jobs, list => [...list, job])
  return job
}

async function describe($: $): Promise<string> {
  const now = await $.clock.now()
  const list = await read($, jobs)
  if (list.length === 0) return 'No ticks scheduled.'
  return list
    .map(j => `${j.id}  in ${fmt(j.dueAt - now)}${j.everyMs ? `, every ${fmt(j.everyMs)} (${j.fired}/${j.maxFires})` : ''}  ${j.prompt.slice(0, 70)}`)
    .join('\n')
}

// turnId → start time; a turn whose complete never arrives stops blocking after STUCK_MS.
const running = new Map<string, number>()
const STUCK_MS = 2 * 3_600_000
let isSubmitting = false

async function poll($: $): Promise<void> {
  const now = await $.clock.now()
  const list = await read($, jobs)
  $.ui.status(list.length === 0 ? undefined : `tick: ${list.length} · next ${fmt(Math.min(...list.map(j => j.dueAt)) - now)}`)
  for (const [id, at] of running) if (now - at > STUCK_MS) running.delete(id)
  if (isSubmitting || running.size > 0) return
  const due = list.filter(j => j.dueAt <= now).sort((a, b) => a.dueAt - b.dueAt)[0]
  if (due === undefined) return
  const fired = due.fired + 1
  await update($, jobs, all =>
    due.everyMs === null || fired >= due.maxFires
      ? all.filter(j => j.id !== due.id)
      : all.map(j => (j.id === due.id ? { ...j, fired, dueAt: now + (due.everyMs ?? 0) } : j)),
  )
  isSubmitting = true
  try {
    await $.prompt.submit({ text: `[tick ${due.id}${due.everyMs ? ` ${fired}/${due.maxFires}` : ''}] ${due.prompt}` })
  } finally {
    isSubmitting = false
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'tick',
      description: 'Schedule a local prompt: /tick 20m <prompt> · /tick every 30m <prompt> · /tick stop [id] · /tick',
      argumentHint: '[every] <30s|20m|2h> <prompt> | stop [id]',
    })
    await $.tool.register({
      name: 'wake',
      description:
        'Wake this session later with a prompt, from inside this Claude Code process. Prefer it over ScheduleWakeup/CronCreate for waits inside a live session: it uses none of the account routine quota. It does not survive the process exiting. Minimum 60s; recurring wakes stop after 48 fires. `cancel` with an id removes one.',
      inputSchema: {
        type: 'object',
        properties: {
          seconds: { type: 'integer', minimum: 60, description: 'Delay before the wake (and the period when every is true).' },
          prompt: { type: 'string', description: 'The prompt the session receives on waking.' },
          every: { type: 'boolean', description: 'Repeat at this period.' },
          cancel: { type: 'string', description: 'Id of a scheduled wake to cancel; other fields ignored.' },
        },
      },
    })
    $.clock.every(POLL_MS, () => void poll($))
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    running.set(e.turnId, await $.clock.now())
    return next(e)
  })

  on('turn.complete', ($, e, next) => {
    running.delete(e.turnId)
    return next(e)
  })

  on('tool.call', { tool: 'mcp__tick__wake' }, async ($, e) => {
    const input = e as unknown as { seconds?: number; prompt?: string; every?: boolean; cancel?: string }
    if (input.cancel) {
      const before = (await read($, jobs)).length
      await update($, jobs, list => list.filter(j => j.id !== input.cancel))
      const removed = before - (await read($, jobs)).length
      return { result: removed ? `Cancelled ${input.cancel}.` : `No wake named ${input.cancel}.` }
    }
    if (!input.prompt || !input.seconds || input.seconds < 60) {
      return { result: 'Needs prompt and seconds >= 60.', isError: true }
    }
    const job = await schedule($, input.prompt, input.seconds * 1000, input.every === true)
    return { result: `Scheduled ${job.id} in ${fmt(input.seconds * 1000)}${job.everyMs ? ', recurring' : ''}.\n${await describe($)}` }
  })

  on('command.run', { command: 'tick' }, async ($, e) => {
    const args = e.args.trim()
    if (args === '') return { text: await describe($) }
    const stop = /^stop(?:\s+(\S+))?$/.exec(args)
    if (stop) {
      await update($, jobs, list => (stop[1] ? list.filter(j => j.id !== stop[1]) : []))
      return { text: await describe($) }
    }
    const m = /^(every\s+)?(\S+)\s+([\s\S]+)$/.exec(args)
    const ms = m ? parseDuration(m[2] ?? '') : null
    if (!m || ms === null || ms < MIN_MS) {
      return { text: 'Usage: /tick [every] <60s|20m|2h> <prompt> · /tick stop [id] · /tick' }
    }
    const job = await schedule($, (m[3] ?? '').trim(), ms, m[1] !== undefined)
    return { text: `Scheduled ${job.id}.\n${await describe($)}` }
  })
}
