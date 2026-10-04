import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Question, Snapshot } from '../types'

// The control plane the SessionStart digest prints as text, drawn instead
// above the prompt where it costs the model nothing. Data: `pulse funnel
// --json` (0.4s) + `questions_view --json` + the inbox `pulse tick` writes;
// never `pulse status`, which takes ~45s.

const PANE = 'questions'
const REFRESH_MS = 10 * 60_000
const STALE_MS = 30 * 86_400_000

const snap = atom({ plugin: 'control-plane', key: 'snap' } as const, null)
const questions = atom({ plugin: 'control-plane', key: 'questions' } as const, [])
const isHidden = atom({ plugin: 'control-plane', key: 'isHidden' } as const, false)
const note = atom({ plugin: 'control-plane', key: 'note' } as const, '')

type $ = EngineInterface

async function paths($: $) {
  const home = (await $.env.get('HOME')) ?? '/Users/alien'
  return {
    repo: `${home}/Projects/agent-infra`,
    uv: `${home}/.local/bin/uv`,
    inbox: `${home}/.claude/control-plane-inbox.md`,
  }
}

async function runJson($: $, script: readonly string[]): Promise<any> {
  const p = await paths($)
  const r = await $.process.run([p.uv, 'run', 'python3', ...script], { cwd: p.repo, timeoutMs: 60_000 })
  if (r.exitCode !== 0) throw new Error(`${script[0]} exit ${r.exitCode}: ${r.stderr.trim().slice(-120)}`)
  return JSON.parse(r.stdout)
}

export function driftCount(inbox: string): number {
  const section = inbox.split(/^## /m).find(s => s.startsWith('Drift flags'))
  return section ? (section.match(/^- \*\*/gm) ?? []).length : 0
}

async function refresh($: $): Promise<void> {
  try {
    const [funnel, view] = await Promise.all([
      runJson($, ['scripts/pulse.py', 'funnel', '--json']),
      runJson($, ['scripts/questions_view.py', '--json']),
    ])
    const now = await $.clock.now()
    const qs: Question[] = view.questions.map((q: Question) => ({
      id: q.id, source: q.source, prompt: q.prompt, created: q.created, ref: q.ref,
    }))
    const { inbox } = await paths($)
    let drift = 0
    let inboxAgeH: number | null = null
    if (await $.fs.exists(inbox)) {
      inboxAgeH = Math.floor((now - (await $.fs.stat(inbox)).mtimeMs) / 3_600_000)
      drift = driftCount(await $.fs.read(inbox))
    }
    const fresh: Snapshot = {
      questions: qs.length,
      stale: qs.filter(q => q.created !== '' && now - Date.parse(q.created) > STALE_MS).length,
      rsi: funnel.rsi_close_pending,
      quarantine: funnel.quarantine_pending,
      drift,
      inboxAgeH,
      error: null,
    }
    await update($, questions, () => qs)
    await update($, snap, () => fresh)
  } catch (err) {
    const error = String(err).slice(0, 160)
    await update($, snap, s => ({
      ...(s ?? { questions: 0, stale: 0, rsi: 0, quarantine: 0, drift: 0, inboxAgeH: null }),
      error,
    }))
  }
}

async function answer($: $, q: Question, text: string): Promise<void> {
  const value = text.trim()
  if (value === '') return
  const p = await paths($)
  const r = await $.process.run(
    [p.uv, 'run', 'python3', 'scripts/human_md_answer.py', q.ref, value],
    { cwd: p.repo, timeoutMs: 30_000 },
  )
  await update($, note, () =>
    r.exitCode === 0 ? `Answered: ${q.prompt.slice(0, 60)}` : `Not written: ${r.stderr.trim().slice(-120)}`,
  )
  await refresh($)
}

const openPane = ($: $) => $.ui.open({ id: PANE, title: 'Questions for you', focus: true, closeOnEscape: true })

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    if (e.isInteractive) {
      await $.command.register({ name: 'questions', description: 'Open the questions pane (answer HUMAN.md asks inline)' })
      await $.command.register({ name: 'control-plane', description: 'Refresh and show the control-plane band' })
      void refresh($)
      $.clock.every(REFRESH_MS, () => void refresh($))
    }
    return next(e)
  })

  on('command.run', { command: 'questions' }, async $ => {
    await refresh($)
    await openPane($)
    return { text: 'Questions pane opened.' }
  })

  on('command.run', { command: 'control-plane' }, async $ => {
    await update($, isHidden, () => false)
    await refresh($)
    const s = await read($, snap)
    return { text: s?.error ? `[DEGRADED] ${s.error}` : 'Control-plane band refreshed.' }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const s = await read($, snap)
    if (e.props.hasSurvey || s === null || (await read($, isHidden))) return next(e)
    if (s.error === null && s.questions + s.rsi + s.quarantine + s.drift === 0) return next(e)

    const { Box, Button, Text } = $.ui.resolve(e)
    return (
      <Box>
        {s.error !== null ? (
          <Text color="warning">[DEGRADED] control plane: {s.error} </Text>
        ) : (
          <Text dimColor>▸ control plane{s.inboxAgeH === null ? '' : ` ${s.inboxAgeH}h`} </Text>
        )}
        {s.questions > 0 && (
          <Button
            key="questions"
            label={`questions ${s.questions}${s.stale > 0 ? ` (${s.stale} stale)` : ''}`}
            onPress={() => void openPane($)}
          />
        )}
        {s.rsi > 0 && (
          <Button
            key="rsi"
            label={`rsi close ${s.rsi}`}
            onPress={() => void $.prompt.fill({ text: '/rsi close', mode: 'replace' })}
          />
        )}
        <Text dimColor> quarantine {s.quarantine} · drift {s.drift} </Text>
        <Button key="hide" label="hide" plain dimColor onPress={() => void update($, isHidden, () => true)} />
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const els = $.ui.resolve(e)
    const { Box, Button, Text } = els
    const qs = await read($, questions)
    const msg = await read($, note)
    return (
      <Box flexDirection="column">
        {msg !== '' && <Text color="success">{msg}</Text>}
        {qs.length === 0 && <Text dimColor>No open questions.</Text>}
        {qs.map(q => (
          <Box key={q.id} flexDirection="column" marginBottom={1}>
            <Text bold>{q.prompt}</Text>
            <Text dimColor>
              {q.source} · {q.created} · {q.ref}
            </Text>
            {q.source === 'human-md' && 'Input' in els ? (
              <els.Input
                key={`answer-${q.id}`}
                placeholder="your answer; Enter writes it into HUMAN.md"
                onSubmit={value => void answer($, q, value)}
              />
            ) : (
              <Button
                key={`open-${q.id}`}
                label="ask Claude about it"
                onPress={() =>
                  void $.prompt.fill({
                    text: `Read ${q.ref} and give me the decision it needs, with your recommendation.`,
                    mode: 'replace',
                  })
                }
              />
            )}
          </Box>
        ))}
      </Box>
    )
  })
}
