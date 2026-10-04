export type Row = { kind: 'agent' | 'task' | 'bgrun' | 'lane'; name: string; state: string; detail: string; isLive: boolean }

declare module 'claude-code' {
  interface PluginState {
    fleet: { rows: Row[]; tasks: Row[]; refreshedAt: number; error: string }
  }
}
