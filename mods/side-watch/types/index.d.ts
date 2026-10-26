export type Kind = 'claim' | 'stance' | 'stuck' | 'heads-up' | 'you-should-know'

export type Note = { kind: Kind; line: string; detail: string; at: string; injected: boolean }

export type Usage = { input: number; output: number; cacheRead: number; cacheWrite: number }

export type Check = {
  watcher: 'turn-end' | 'stuck'
  turnId: string
  step: number
  at: string
  outcome: 'none' | 'notes' | 'unanswered' | 'unparsed'
  notes: number
  reason: string
  usage: Usage | null
}

declare module 'claude-code' {
  interface PluginState {
    'side-watch': {
      notes: Note[]
      checks: Check[]
      isOn: boolean
      inject: boolean
      relay: boolean
      stuckEvery: number
      lastRelayAt: number
      noBackoff: boolean
    }
  }
}
