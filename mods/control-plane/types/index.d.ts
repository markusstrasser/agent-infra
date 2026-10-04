export type Snapshot = {
  questions: number
  stale: number
  rsi: number
  quarantine: number
  drift: number
  inboxAgeH: number | null
  error: string | null
}

export type Question = { id: string; source: string; prompt: string; created: string; ref: string }

declare module 'claude-code' {
  interface PluginState {
    'control-plane': { snap: Snapshot | null; questions: Question[]; isHidden: boolean; note: string }
  }
}
