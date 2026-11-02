import type { On, RenderElement } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { mergeNotes, needsTurnEndCheck, offerFor, parseReply, turnEndPrompt } from '../hooks/register'

const USAGE = { input_tokens: 12, output_tokens: 9, cache_read_input_tokens: 40_000, cache_creation_input_tokens: 0 }

type Seen = { prompts: string[]; appended: string[]; notified: string[]; files: Record<string, string> }

function host(on: On, reply: (prompt: string) => string, seen: Seen) {
  mock.env(on, { HOME: '/h' })
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('session.id', () => ({ value: 'sess-1' }))
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('model.fork', ($, e) => {
    const p = typeof e.prompt === 'string' ? e.prompt : JSON.stringify(e.prompt)
    seen.prompts.push(p)
    return { value: { isAnswered: true, text: reply(p), usage: USAGE } }
  })
  on('session.append', ($, e, next) => {
    const block = e.message.content[0] as { text?: string } | undefined
    seen.appended.push(block?.text ?? '')
    return next(e)
  })
  on('ui.notify', ($, e) => {
    seen.notified.push(e.text)
    return { value: { isSent: true, channel: 'terminal_bell' } }
  })
  on('ui.status', () => ({ value: undefined }))
  on('fs.write', ($, e) => {
    seen.files[e.path] = e.text
    return { value: undefined }
  })
  on('fs.exists', ($, e) => ({ value: e.path in seen.files }))
  on('fs.read', ($, e) => ({ value: seen.files[e.path] ?? '' }))
  return mock.clock(on, { now: Date.parse('2026-10-26T00:00:00Z') })
}

const fresh = (): Seen => ({ prompts: [], appended: [], notified: [], files: {} })

const turn = ($: Engine, id: string, answer: string, agentId?: string) =>
  $.turn.complete({ turnId: id, answer, durationMs: 1, isAborted: false, reason: 'answer', ...(agentId ? { agentId } : {}) })

test('parses tagged lines, NONE and garbage, keeping only the watcher’s tags', () => {
  expect(parseReply('NONE', ['claim', 'stance'])).toEqual({ outcome: 'none', found: [] })
  expect(parseReply('CLAIM: said tests pass, no pytest run\n**STANCE:** flipped on caching', ['claim', 'stance'])).toEqual({
    outcome: 'notes',
    found: [
      { kind: 'claim', line: 'said tests pass, no pytest run' },
      { kind: 'stance', line: 'flipped on caching' },
    ],
  })
  expect(parseReply('STUCK: retried 4x', ['claim', 'stance']).outcome).toBe('unparsed')
  expect(parseReply('Looks fine to me', ['stuck']).outcome).toBe('unparsed')
})

test('turn-end prompt carries the final message the fork cannot see', () => {
  expect(turnEndPrompt('All 12 tests pass.')).toContain('<final_message>\nAll 12 tests pass.\n</final_message>')
})

test('a CLAIM at turn end is injected for the model and logged with tokens', async ($, on) => {
  const seen = fresh()
  const clock = host(on, () => 'CLAIM: "committed" but no git commit ran', seen)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await turn($, 't-sub', 'sub report', 'agent-1')
  await clock.advance(1_000)
  expect(seen.prompts.length).toBe(0)
  await turn($, 't1', 'Done, committed.')
  await clock.advance(1_000)
  expect(seen.prompts.length).toBe(1)
  expect(seen.appended[0]).toContain('side-watch · CLAIM')
  expect(seen.appended[0]).toContain('no git commit ran')
  const log = JSON.parse(seen.files['/h/.claude/side-watch/sess-1.json'] ?? '{}')
  expect(log.checks[0]).toMatchObject({ watcher: 'turn-end', outcome: 'notes', usage: { output: 9, cacheRead: 40_000 } })
})

test('NONE stays quiet', async ($, on) => {
  const seen = fresh()
  const clock = host(on, () => 'NONE', seen)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await turn($, 't1', 'All tests pass.')
  await clock.advance(1_000)
  expect(seen.prompts.length).toBe(1)
  expect(seen.appended.length).toBe(0)
})

test('a plain answer with no claim and no pushback skips the fork', async ($, on) => {
  const seen = fresh()
  const clock = host(on, () => 'NONE', seen)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await turn($, 't1', 'Here is the answer.')
  await clock.advance(1_000)
  expect(seen.prompts.length).toBe(0)
})

test('the gate fires on outcome claims and on pushback', () => {
  expect(needsTurnEndCheck('Fixed it and committed.', '')).toBe(true)
  expect(needsTurnEndCheck('Both suites pass ✓', '')).toBe(true)
  expect(needsTurnEndCheck('The cache is keyed by path.', 'are you sure about that?')).toBe(true)
  expect(needsTurnEndCheck('Here is how the cache works.', 'how does the cache work?')).toBe(false)
})

test('/watch now runs both watchers; STUCK notifies the person and is not injected', async ($, on) => {
  const seen = fresh()
  host(on, p => (p.includes('Is the assistant stuck') ? 'STUCK: ran the same failing build 4x; read the error first' : 'NONE'), seen)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  const r = await $.command.run({
    command: 'watch',
    args: 'now',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: false, columns: 120 },
  })
  expect(JSON.stringify(r)).toContain('stuck: notes')
  expect(seen.notified[0]).toContain('same failing build')
  expect(seen.appended.length).toBe(0)
})

test('reads the built-in card for this session only', () => {
  const view = { kind: 'offer', line: 'Typing past cards backs off.', explanation: '**Backoff**\nbody', shownAt: 5 }
  expect(offerFor([{ id: 'other', view }, { id: 'sess-1', tag: 'Heads up', view }], 'sess-1')).toEqual({
    line: 'Typing past cards backs off.',
    explanation: '**Backoff**\nbody',
    shownAt: 5,
    tag: 'Heads up',
  })
  expect(offerFor([{ id: 'sess-1', view: { kind: 'asked', line: 'x' } }], 'sess-1')).toBeNull()
  expect(offerFor(undefined, 'sess-1')).toBeNull()
})

const BAND = {
  plugin: 'side-watch',
  surface: 'terminal',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 8, bodyColumns: 120, scroll: { offset: 0, bodyRows: 8 }, view: {} },
} as const

const LOG = {
  plugin: 'side-watch',
  surface: 'terminal',
  component: 'Pane',
  requestId: 'side-watch-log',
  props: { title: 'side-watch: autoinjected', isFocused: false, bodyColumns: 120, placement: 'dock', scroll: { offset: 0, bodyRows: 20 }, view: {} },
} as const

function withUi(on: On, opened: string[]) {
  on('ui.render', ($, e) => h($.ui.resolve(e).Box, {}) as RenderElement)
  on('ui.open', ($, e) => {
    opened.push(e.id)
    return { value: { isPlaced: true } }
  })
}

test('an injected note leaves the band; a counter opens the log pane listing it', async ($, on) => {
  const seen = fresh()
  const opened: string[] = []
  const clock = host(on, () => 'CLAIM: "committed" but no git commit ran', seen)
  withUi(on, opened)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await turn($, 't1', 'Done, committed.')
  await clock.advance(1_000)
  const band = await $.ui.mount(BAND)
  expect(await band.find({ type: 'Text', text: /no git commit ran/ })).toBeUndefined()
  expect(await band.find({ key: 'clear' })).toBeUndefined()
  expect((await band.find({ key: 'log' }))?.text).toContain('1 autoinjected')
  await band.press({ key: 'log' })
  expect(opened).toEqual(['side-watch-log'])
  await band.unmount()
  const pane = await $.ui.mount(LOG)
  expect(await pane.find({ type: 'Text', text: /no git commit ran/ })).toBeDefined()
  await pane.unmount()
  const log = JSON.parse(seen.files['/h/.claude/side-watch/sess-1.json'] ?? '{}')
  expect(log.injected[0]).toMatchObject({ kind: 'claim', injected: true })
})

test('STUCK stays in the band until cleared', async ($, on) => {
  const seen = fresh()
  const opened: string[] = []
  host(on, () => 'STUCK: polled the same log five times', seen)
  withUi(on, opened)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'watch', args: 'now', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 120 } })
  const band = await $.ui.mount(BAND)
  expect(await band.find({ type: 'Text', text: /polled the same log/ })).toBeDefined()
  expect(await band.find({ key: 'log' })).toBeUndefined()
  await band.press({ key: 'clear' })
  expect(await band.find({ type: 'Text', text: /polled the same log/ })).toBeUndefined()
  await band.unmount()
})

test('a restarted session restores its injected list from the log', async ($, on) => {
  const seen = fresh()
  const opened: string[] = []
  host(on, () => 'NONE', seen)
  withUi(on, opened)
  const saved = { session_id: 'sess-1', checks: [], injected: [{ kind: 'heads-up', line: 'old card', detail: 'why', at: '2026-11-01T17:00:00Z', injected: true }] }
  seen.files['/h/.claude/side-watch/sess-1.json'] = JSON.stringify(saved)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  const res = await $.command.run({ command: 'watch', args: 'log', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 120 } })
  expect(res?.text).toContain('1 autoinjected')
  const pane = await $.ui.mount(LOG)
  expect(await pane.find({ type: 'Text', text: /old card/ })).toBeDefined()
  await pane.unmount()
})

test('the injected log only grows: merge keeps both sides, dedupes, sorts by time', () => {
  const a = { kind: 'claim' as const, line: 'x', detail: '', at: '2026-11-02T00:00:00Z', injected: true }
  const b = { kind: 'heads-up' as const, line: 'y', detail: '', at: '2026-11-01T00:00:00Z', injected: true }
  expect(mergeNotes([a], [b, a]).map(n => n.line)).toEqual(['y', 'x'])
  expect(mergeNotes([a, b], [])).toHaveLength(2)
})
