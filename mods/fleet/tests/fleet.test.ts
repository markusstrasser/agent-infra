import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

import { parseLanes } from '../hooks/register'

const NOW = Date.parse('2026-10-04T00:00:00Z')
const LANES = `NAME                 STATE      LOG-AGE  STARTED               DIRTY REVIEW
binary-sweep         DONE:0     32d      2026-09-02T08:45:07Z  30    -
port-x               RUNNING    40s      2026-10-04T00:00:00Z  2     -
`

test('lane rows keep only lanes that are not DONE', () => {
  expect(parseLanes(LANES)).toEqual([{ kind: 'lane', name: 'port-x', state: 'RUNNING', detail: 'log 40s', isLive: true }])
})

function host(on: On) {
  mock.env(on, { HOME: '/h', TMPDIR: '/t/' })
  mock.clock(on, { now: NOW })
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('agent.list', () => ({
    value: [
      { id: 'a1', type: 'explorer', name: 'scout', description: 'find callers', status: 'running' },
      { id: 'a2', type: 'opus-low', description: 'port', status: 'completed' },
    ],
  }))
  on('fs.exists', () => ({ value: true }))
  on('fs.list', () => ({
    value: [
      { name: 'grind.pid', kind: 'file', size: 1, mtimeMs: NOW, isLink: false },
      { name: 'grind.log', kind: 'file', size: 1, mtimeMs: NOW - 300_000, isLink: false },
    ],
  }))
  on('process.run', () => ({ value: { exitCode: 0, stdout: LANES, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }))
}

test('pane lists live work first and dims finished work', async ($, on) => {
  host(on)
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'fleet', args: '', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 160 } })
  const ui = await $.ui.mount({
    plugin: 'fleet',
    surface: 'terminal',
    component: 'Pane',
    requestId: 'fleet',
    props: { title: 'Fleet', isFocused: false, bodyColumns: 120, placement: 'dock', scroll: { offset: 0, bodyRows: 20 }, view: {} },
  })
  expect(await ui.find({ type: 'Text', text: /3 live · 1 finished/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /grind\s+running\s+log quiet 5m/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /port-x/ })).toBeDefined()
  const done = await ui.find({ type: 'Text', text: /opus-low/ })
  expect(done?.props.dimColor).toBe(true)
  await ui.unmount()
})
