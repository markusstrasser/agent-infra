import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

const T0 = Date.parse('2026-10-04T00:00:00Z')

function host(on: On, submitted: string[]) {
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('tool.register', ($, e) => ({ value: { tool: `mcp__tick__${e.name}` } }))
  on('turn.start', ($, e) => ({ turnId: e.turnId }))
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('prompt.submit', ($, e) => {
    submitted.push(e.text)
    return { text: e.text }
  })
  return mock.clock(on, { now: T0 })
}

const run = ($: Engine, args: string) =>
  $.command.run({ command: 'tick', args, origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 120 } })

test('a one-shot tick fires once when due and idle', async ($, on) => {
  const submitted: string[] = []
  const clock = host(on, submitted)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await run($, '2m check the CI run')
  await clock.advance(60_000)
  expect(submitted).toHaveLength(0)
  await clock.advance(90_000)
  expect(submitted).toEqual(['[tick t1] check the CI run'])
  await clock.advance(600_000)
  expect(submitted).toHaveLength(1)
  expect((await run($, '')).text).toBe('No ticks scheduled.')
})

test('a recurring tick waits while a turn runs, then repeats', async ($, on) => {
  const submitted: string[] = []
  const clock = host(on, submitted)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await run($, 'every 1m status')
  await $.turn.start({ text: 'busy', turnId: 'u1' })
  await clock.advance(120_000)
  expect(submitted).toHaveLength(0)
  await $.turn.complete({ turnId: 'u1', answer: '', durationMs: 1, isAborted: false, reason: 'answer' })
  await clock.advance(15_000)
  expect(submitted).toEqual(['[tick t1 1/48] status'])
  await clock.advance(61_000)
  expect(submitted).toHaveLength(2)
  await run($, 'stop')
  await clock.advance(300_000)
  expect(submitted).toHaveLength(2)
})

test('rejects sub-minute and malformed schedules', async ($, on) => {
  host(on, [])
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  expect((await run($, '30s too soon')).text).toMatch(/^Usage/)
  expect((await run($, 'soon do it')).text).toMatch(/^Usage/)
})
