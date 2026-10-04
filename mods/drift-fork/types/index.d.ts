export type Check = {
  turn: number
  at: string
  verdict: 'ok' | 'drift' | 'unanswered'
  line: string
  usage: { input: number; output: number; cacheRead: number; cacheWrite: number } | null
}

declare module 'claude-code' {
  interface PluginState {
    'drift-fork': { turns: number; every: number; isOn: boolean; inject: boolean; checks: Check[] }
  }
}
