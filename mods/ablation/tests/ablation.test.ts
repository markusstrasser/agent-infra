import type { InstructionFile, On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

import { assign, bucket } from '../hooks/register'

const file = (path: string, content = 'x'.repeat(10)): InstructionFile => ({ path, kind: 'user', content })
const FILES = [file('/h/.claude/CLAUDE.md'), file('/h/.claude/rules/wakeup-cadence.md', 'y'.repeat(40))]
const EXP = { id: 'no-wakeup', drop: ['rules/wakeup-cadence.md'], treatmentShare: 0.5, active: true }

test('bucket is stable and spreads across sessions', async () => {
  expect(await bucket('s1', 'e')).toBe(await bucket('s1', 'e'))
  const draws = await Promise.all(Array.from({ length: 200 }, (_, i) => bucket(`s${i}`, 'e')))
  const treated = draws.filter(d => d < 0.5).length
  expect(treated).toBeGreaterThan(70)
  expect(treated).toBeLessThan(130)
})

test('treatment drops only the named file; control keeps all', async () => {
  const all = await assign('s', [{ ...EXP, treatmentShare: 1 }], FILES)
  expect(all.kept.map(f => f.path)).toEqual(['/h/.claude/CLAUDE.md'])
  expect(all.assignments[0]).toMatchObject({ arm: 'treatment', droppedChars: 40 })
  const none = await assign('s', [{ ...EXP, treatmentShare: 0 }], FILES)
  expect(none.kept).toHaveLength(2)
  expect(none.assignments[0]).toMatchObject({ arm: 'control', dropped: [] })
})

function host(on: On, config: string | null, written: Record<string, string>) {
  mock.env(on, { HOME: '/h' })
  mock.clock(on, { now: Date.parse('2026-10-04T00:00:00Z') })
  on('session.id', () => ({ value: 'sess-1' }))
  on('session.cwd', () => ({ value: '/h/p' }))
  on('fs.exists', ($, e) => ({ value: e.path === '/h/.claude/harness-ablation.json' && config !== null }))
  on('fs.read', () => ({ value: config ?? '' }))
  on('fs.write', ($, e) => {
    written[e.path] = e.text
    return { value: undefined }
  })
  on('prompt.context', ($, e) => ({ blocks: e.blocks, instructionFiles: e.instructionFiles }))
}

test('prompt.context drops the file in treatment and records the arm', async ($, on) => {
  const written: Record<string, string> = {}
  host(on, JSON.stringify({ experiments: [{ ...EXP, treatmentShare: 1 }] }), written)
  const r = await $.prompt.context({ blocks: [{ name: 'claudeMd', text: '...' }], instructionFiles: FILES })
  expect(r.instructionFiles?.map(f => f.path)).toEqual(['/h/.claude/CLAUDE.md'])
  const rec = JSON.parse(written['/h/.claude/harness-ablation/sess-1.json'] ?? '{}')
  expect(rec.assignments[0]).toMatchObject({ experiment: 'no-wakeup', arm: 'treatment' })
})

test('no config passes the context through and writes nothing', async ($, on) => {
  const written: Record<string, string> = {}
  host(on, null, written)
  const r = await $.prompt.context({ blocks: [], instructionFiles: FILES })
  expect(r.instructionFiles).toHaveLength(2)
  expect(Object.keys(written)).toHaveLength(0)
})
