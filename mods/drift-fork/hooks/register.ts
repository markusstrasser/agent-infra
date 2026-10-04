import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Check } from '../types'

// A semantic drift check a shell hook cannot afford: $.model.fork asks one
// question over the session's own transcript, served from its prompt cache.
// The verdict goes to the person (toast/status), not the model, unless
// `/drift inject` is on. Every check's tokens land in
// ~/.claude/drift-fork/<session>.json (eval-token-costs rule).

const turns = atom({ plugin: 'drift-fork', key: 'turns' } as const, 0)
const every = atom({ plugin: 'drift-fork', key: 'every' } as const, 10)
const isOn = atom({ plugin: 'drift-fork', key: 'isOn' } as const, true)
const inject = atom({ plugin: 'drift-fork', key: 'inject' } as const, false)
const checks = atom({ plugin: 'drift-fork', key: 'checks' } as const, [])

export const QUESTION = [
  'Side check from the drift-fork mod, not from the user. Nobody in the main thread reads this reply.',
  'Judge the conversation so far. Reply exactly `OK` if the work is on track.',
  'Reply `DRIFT: <one sentence naming the evidence>` if any of these holds:',
  "(1) the assistant is working on something other than the user's latest request;",
  '(2) it has repeated the same failing action or approach three or more times;',
  '(3) it is re-deriving or reversing a decision the user already made;',
  '(4) it reported something done or verified with no evidence for it in the transcript.',
  'No other text.',
].join('\n')

type $ = EngineInterface

export function parseVerdict(text: string): { verdict: 'ok' | 'drift'; line: string } {
  const t = text.trim()
  const m = /^DRIFT:\s*([\s\S]+)$/i.exec(t)
  if (m) return { verdict: 'drift', line: (m[1] ?? '').split('\n')[0]!.trim() }
  return /^OK\b/i.test(t) ? { verdict: 'ok', line: '' } : { verdict: 'drift', line: `unparsed reply: ${t.slice(0, 120)}` }
}

let isChecking = false

async function check($: $, turn: number): Promise<Check> {
  isChecking = true
  try {
    const r = await $.model.fork({ prompt: QUESTION })
    const at = new Date(await $.clock.now()).toISOString()
    const usage =
      'usage' in r
        ? {
            input: r.usage.input_tokens,
            output: r.usage.output_tokens,
            cacheRead: r.usage.cache_read_input_tokens,
            cacheWrite: r.usage.cache_creation_input_tokens,
          }
        : null
    const result: Check = r.isAnswered
      ? { turn, at, usage, ...parseVerdict(r.text) }
      : { turn, at, usage, verdict: 'unanswered', line: r.reason }
    const all = await update($, checks, list => [...list, result].slice(-200))
    const sessionId = await $.session.id()
    const home = (await $.env.get('HOME')) ?? '/Users/alien'
    await $.fs.write(`${home}/.claude/drift-fork/${sessionId}.json`, JSON.stringify({ session_id: sessionId, checks: all }, null, 2))
    if (result.verdict === 'drift') {
      $.ui.toast(`drift (turn ${turn}): ${result.line}`, { timeoutMs: 15_000 })
      $.ui.status(`drift: ${result.line.slice(0, 60)}`)
      if (await read($, inject)) {
        await $.session.append({
          message: {
            type: 'user',
            content: [{ type: 'text', text: `[drift-fork check at turn ${turn}, automated, not the user] ${result.line}` }],
          },
        })
      }
    } else {
      $.ui.status(result.verdict === 'ok' ? undefined : `drift check failed: ${result.line}`)
    }
    return result
  } finally {
    isChecking = false
  }
}

function summary(list: readonly Check[]): string {
  if (list.length === 0) return 'No drift checks yet.'
  const tok = list.reduce(
    (n, c) => ({ out: n.out + (c.usage?.output ?? 0), fresh: n.fresh + (c.usage?.input ?? 0) + (c.usage?.cacheWrite ?? 0), cached: n.cached + (c.usage?.cacheRead ?? 0) }),
    { out: 0, fresh: 0, cached: 0 },
  )
  const lines = list.slice(-8).map(c => `turn ${c.turn}: ${c.verdict}${c.line ? ` · ${c.line}` : ''}`)
  return [...lines, `${list.length} checks · out ${tok.out} tok · uncached in ${tok.fresh} · cache read ${tok.cached}`].join('\n')
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'drift',
      description: 'Drift checks: /drift · /drift now · /drift on|off · /drift every N · /drift inject on|off',
      argumentHint: 'now | on | off | every N | inject on|off',
    })
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId !== undefined || e.reason !== 'answer' || !(await read($, isOn))) return result
    const n = await update($, turns, t => t + 1)
    if (n % (await read($, every)) === 0 && !isChecking) {
      $.clock.after(1_000, () => void check($, n))
    }
    return result
  })

  on('command.run', { command: 'drift' }, async ($, e) => {
    const a = e.args.trim().split(/\s+/).filter(Boolean)
    if (a[0] === 'now') {
      const c = await check($, await read($, turns))
      return { text: `${c.verdict}${c.line ? `: ${c.line}` : ''}` }
    }
    if (a[0] === 'on' || a[0] === 'off') await update($, isOn, () => a[0] === 'on')
    if (a[0] === 'every' && Number(a[1]) >= 3) await update($, every, () => Math.floor(Number(a[1])))
    if (a[0] === 'inject' && (a[1] === 'on' || a[1] === 'off')) await update($, inject, () => a[1] === 'on')
    const state = `${(await read($, isOn)) ? 'on' : 'off'} · every ${await read($, every)} turns · inject ${(await read($, inject)) ? 'on' : 'off'}`
    return { text: `${state}\n${summary(await read($, checks))}` }
  })
}
