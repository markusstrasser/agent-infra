import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { parseVerdict } from '../hooks/register'

const USAGE = { input_tokens: 12, output_tokens: 9, cache_read_input_tokens: 40_000, cache_creation_input_tokens: 0 }

function host(on: On, reply: string, seen: { forks: number; toasts: string[]; files: Record<string, string> }) {
  mock.env(on, { HOME: '/h' })
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('session.id', () => ({ value: 'sess-1' }))
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('model.fork', () => {
    seen.forks += 1
    return { value: { isAnswered: true, text: reply, usage: USAGE } }
  })
  on('ui.toast', ($, e) => {
    seen.toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.status', () => ({ value: undefined }))
  on('fs.write', ($, e) => {
    seen.files[e.path] = e.text
    return { value: undefined }
  })
  return mock.clock(on, { now: Date.parse('2026-10-04T00:00:00Z') })
}

const turn = ($: Engine, i: number, agentId?: string) =>
  $.turn.complete({ turnId: `u${i}`, answer: 'a', durationMs: 1, isAborted: false, reason: 'answer', ...(agentId ? { agentId } : {}) })

test('parses OK, DRIFT and garbage', () => {
  expect(parseVerdict('OK')).toEqual({ verdict: 'ok', line: '' })
  expect(parseVerdict('DRIFT: retried pytest 4x\nmore')).toEqual({ verdict: 'drift', line: 'retried pytest 4x' })
  expect(parseVerdict('Sure! Looks fine').verdict).toBe('drift')
})

test('forks on every 10th main-thread turn, toasts drift, logs tokens', async ($, on) => {
  const seen = { forks: 0, toasts: [] as string[], files: {} as Record<string, string> }
  const clock = host(on, 'DRIFT: re-litigating the band design', seen)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  for (let i = 1; i <= 9; i++) await turn($, i)
  await turn($, 99, 'subagent-1')
  await clock.advance(2_000)
  expect(seen.forks).toBe(0)
  await turn($, 10)
  await clock.advance(2_000)
  expect(seen.forks).toBe(1)
  expect(seen.toasts[0]).toContain('re-litigating the band design')
  const log = JSON.parse(seen.files['/h/.claude/drift-fork/sess-1.json'] ?? '{}')
  expect(log.checks[0]).toMatchObject({ turn: 10, verdict: 'drift', usage: { output: 9, cacheRead: 40_000 } })
})

test('OK verdicts stay quiet', async ($, on) => {
  const seen = { forks: 0, toasts: [] as string[], files: {} as Record<string, string> }
  const clock = host(on, 'OK', seen)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  for (let i = 1; i <= 10; i++) await turn($, i)
  await clock.advance(2_000)
  expect(seen.forks).toBe(1)
  expect(seen.toasts).toHaveLength(0)
})
