import type { On, RenderElement } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

const BAND = {
  plugin: 'control-plane',
  surface: 'terminal',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 4, bodyColumns: 120, scroll: { offset: 0, bodyRows: 4 }, view: {} },
} as const

const ok = (stdout: string) => ({
  value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
})

function host(on: On, pulseExit = 0) {
  mock.env(on, { HOME: '/h' })
  mock.clock(on, { now: Date.parse('2026-10-04T00:00:00Z') })
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('ui.render', ($, e) => h($.ui.resolve(e).Box, {}) as RenderElement)
  on('fs.exists', () => ({ value: false }))
  on('process.run', ($, e) => {
    const script = e.argv[3]
    if (script === 'scripts/pulse.py') {
      return pulseExit === 0
        ? ok(JSON.stringify({ rsi_close_pending: 2, quarantine_pending: 3 }))
        : { value: { exitCode: pulseExit, stdout: '', stderr: 'db locked', isStdoutTruncated: false, isStderrTruncated: false } }
    }
    return ok(JSON.stringify({
      questions: [{ id: 'q1', source: 'human-md', prompt: '2026-08-01 — pick a lane', created: '2026-08-01', ref: '/h/x/HUMAN.md:3' }],
    }))
  })
}

async function start($: Engine) {
  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })
  await $.command.run({
    command: 'control-plane',
    args: '',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: false, columns: 120 },
  })
}

test('band shows the queue and hides on press', async ($, on) => {
  host(on)
  await start($)
  const ui = await $.ui.mount(BAND)
  expect((await ui.find({ key: 'questions' }))?.text).toContain('questions 1 (1 stale)')
  expect((await ui.find({ key: 'rsi' }))?.text).toContain('rsi close 2')
  expect((await ui.find({ type: 'Text', text: /quarantine 3/ }))).toBeDefined()
  await ui.press({ key: 'hide' })
  expect(await ui.find({ key: 'questions' })).toBeUndefined()
  await ui.unmount()
})

test('a failing source shows DEGRADED, never a silent empty band', async ($, on) => {
  host(on, 1)
  await start($)
  const ui = await $.ui.mount(BAND)
  expect(await ui.find({ type: 'Text', text: /\[DEGRADED\].*db locked/ })).toBeDefined()
  await ui.unmount()
})
