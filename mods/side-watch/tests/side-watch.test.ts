import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { offerFor, parseReply, turnEndPrompt } from '../hooks/register'

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
  await turn($, 't1', 'Here is the answer.')
  await clock.advance(1_000)
  expect(seen.prompts.length).toBe(1)
  expect(seen.appended.length).toBe(0)
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
