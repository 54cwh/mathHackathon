/**
 * WebSocket channel layer — the single owner of the `/v1/ws` envelope and the
 * four implemented push channels (`api/API接口.md` §3). Panels call
 * `subscribe()`; they must not open a socket themselves.
 */

import type { ArenaEvent, FishState } from "./types";

/** Shared envelope: `{v,type,seq,ts,payload}` (`API与系统工程.md §5`). */
export interface WsEnvelope<T = unknown> {
  v: 1;
  type: string;
  seq: number;
  ts: number;
  payload: T;
}

export interface FishStatePayload {
  session_id: string;
  step: number;
  fish: Record<string, FishState>;
}

export interface ArenaEventsPayload {
  session_id: string;
  events: ArenaEvent[];
}

export interface JobProgressPayload {
  job_id: string;
  status: string;
  progress: number;
}

export interface BrainActivationPayload {
  session_id: string;
  step: number;
  fish: Record<string, number[]>;
}

export interface WsHandlers {
  fishState?: (payload: FishStatePayload) => void;
  events?: (payload: ArenaEventsPayload) => void;
  jobProgress?: (payload: JobProgressPayload) => void;
  brainActivation?: (payload: BrainActivationPayload) => void;
}

/** Low-level socket factory; picks `ws`/`wss` from the page protocol. */
export function connectWs(path = "/v1/ws"): WebSocket {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${protocol}://${location.host}${path}`);
}

/**
 * Subscribe to a session's push channels. Returns an unsubscribe function that
 * closes the socket. `sys.hello` / `sys.echo` / `sys.error` are consumed here.
 */
export function subscribe(sessionId: string, handlers: WsHandlers): () => void {
  const ws = connectWs(`/v1/ws?session_id=${encodeURIComponent(sessionId)}`);
  ws.onmessage = (event) => {
    let envelope: WsEnvelope;
    try {
      envelope = JSON.parse(event.data as string) as WsEnvelope;
    } catch {
      return;
    }
    const payload = envelope.payload as never;
    switch (envelope.type) {
      case "arena.fish_state":
        handlers.fishState?.(payload as FishStatePayload);
        break;
      case "arena.events":
        handlers.events?.(payload as ArenaEventsPayload);
        break;
      case "job.progress":
        handlers.jobProgress?.(payload as JobProgressPayload);
        break;
      case "brain.activation":
        handlers.brainActivation?.(payload as BrainActivationPayload);
        break;
      default:
        break;
    }
  };
  return () => ws.close();
}
