import type { EngineInterface, InstructionFile, Register } from 'claude-code'

// Harness A/B without editing CLAUDE.md: each active experiment in
// ~/.claude/harness-ablation.json assigns this session to `treatment` or
// `control` by a hash of (session id, experiment id), so the arm is stable
// across reloads, compactions and subagents. Treatment drops the instruction
// files whose path ends with one of `drop`. Every assignment is recorded in
// ~/.claude/harness-ablation/<session id>.json for agentlogs to join on.
// No config, or no active experiment: the context passes through untouched.

export type Experiment = {
  id: string
  drop: string[]
  treatmentShare: number
  active: boolean
  hypothesis?: string
}

export type Assignment = { experiment: string; arm: 'treatment' | 'control'; dropped: string[]; droppedChars: number }

type $ = EngineInterface

export async function bucket(sessionId: string, experimentId: string): Promise<number> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${sessionId}\0${experimentId}`))
  return new DataView(digest).getUint32(0) / 2 ** 32
}

async function home($: $): Promise<string> {
  return (await $.env.get('HOME')) ?? '/Users/alien'
}

async function experiments($: $): Promise<Experiment[]> {
  const path = `${await home($)}/.claude/harness-ablation.json`
  if (!(await $.fs.exists(path))) return []
  const config = JSON.parse(await $.fs.read(path)) as { experiments?: Experiment[] }
  return (config.experiments ?? []).filter(x => x.active && x.drop.length > 0)
}

export async function assign(
  sessionId: string,
  list: readonly Experiment[],
  files: readonly InstructionFile[],
): Promise<{ kept: InstructionFile[]; assignments: Assignment[] }> {
  let kept = [...files]
  const assignments: Assignment[] = []
  for (const x of list) {
    const arm = (await bucket(sessionId, x.id)) < x.treatmentShare ? 'treatment' : 'control'
    const hit = arm === 'treatment' ? kept.filter(f => x.drop.some(d => f.path.endsWith(d))) : []
    kept = kept.filter(f => !hit.includes(f))
    assignments.push({
      experiment: x.id,
      arm,
      dropped: hit.map(f => f.path),
      droppedChars: hit.reduce((n, f) => n + f.content.length, 0),
    })
  }
  return { kept, assignments }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'ablation', description: "Show this session's harness-ablation arms" })
    return next(e)
  })

  on('prompt.context', async ($, e, next) => {
    const below = await next(e)
    const list = await experiments($)
    const files = below.instructionFiles ?? e.instructionFiles
    if (list.length === 0 || files === undefined) return below
    const sessionId = await $.session.id()
    const { kept, assignments } = await assign(sessionId, list, files)
    const root = `${await home($)}/.claude/harness-ablation`
    await $.fs.write(
      `${root}/${sessionId}.json`,
      JSON.stringify({ session_id: sessionId, cwd: await $.session.cwd(), at: new Date(await $.clock.now()).toISOString(), assignments }, null, 2),
    )
    return kept.length === files.length ? below : { ...below, instructionFiles: kept }
  })

  on('command.run', { command: 'ablation' }, async $ => {
    const path = `${await home($)}/.claude/harness-ablation/${await $.session.id()}.json`
    if (!(await $.fs.exists(path))) return { text: 'No ablation experiment applies to this session.' }
    const rec = JSON.parse(await $.fs.read(path)) as { assignments: Assignment[] }
    return {
      text: rec.assignments
        .map(a => `${a.experiment}: ${a.arm}${a.dropped.length ? ` (dropped ${a.dropped.length} files, ${a.droppedChars} chars)` : ''}`)
        .join('\n'),
    }
  })
}
