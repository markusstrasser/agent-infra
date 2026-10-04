export type Job = {
  id: string
  prompt: string
  everyMs: number | null
  dueAt: number
  fired: number
  maxFires: number
}

declare module 'claude-code' {
  interface PluginState {
    tick: { jobs: Job[]; seq: number }
  }
}
