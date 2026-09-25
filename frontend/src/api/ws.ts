export interface WsEnvelope<T = unknown> {
  v: 1;
  type: string;
  seq: number;
  ts: number;
  payload: T;
}

export function connectWs(path = "/v1/ws"): WebSocket {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${protocol}://${location.host}${path}`);
}
