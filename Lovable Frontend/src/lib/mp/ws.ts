/**
 * WebSocket hook with exponential-backoff reconnect (max 5 attempts).
 * Invalidates React Query caches per message type.
 */
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { QK, USE_MOCK, WS_BASE_URL } from "./api";
import type { WsMessage } from "./types";

export type WsStatus = "connecting" | "connected" | "disconnected" | "offline";

export function useMirrorPupilWebSocket(): WsStatus {
  const qc = useQueryClient();
  const [status, setStatus] = useState<WsStatus>(USE_MOCK ? "offline" : "connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);

  useEffect(() => {
    if (USE_MOCK || typeof window === "undefined") return;
    let stop = false;

    const connect = () => {
      if (stop) return;
      setStatus("connecting");
      let ws: WebSocket;
      try {
        ws = new WebSocket(`${WS_BASE_URL}/ws/updates`);
      } catch {
        setStatus("disconnected");
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        attemptsRef.current = 0;
        setStatus("connected");
      };
      ws.onmessage = (ev) => {
        let msg: WsMessage;
        try {
          msg = JSON.parse(ev.data);
        } catch {
          return;
        }
        switch (msg.type) {
          case "trade":
            qc.invalidateQueries({ queryKey: QK.activeTrades });
            break;
          case "balance":
            qc.invalidateQueries({ queryKey: QK.accounts });
            break;
          case "notification":
            qc.invalidateQueries({ queryKey: ["notifications"] });
            if (msg.data.severity === "CRITICAL" || msg.data.severity === "ERROR") {
              toast.error(msg.data.title);
            } else {
              toast(msg.data.title);
            }
            break;
        }
      };
      ws.onclose = () => {
        if (stop) return;
        setStatus("disconnected");
        if (attemptsRef.current < 5) {
          const wait = 1000 * Math.pow(2, attemptsRef.current);
          attemptsRef.current += 1;
          setTimeout(connect, wait);
        } else {
          toast.warning("Realtime connection lost. Falling back to polling.");
        }
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      stop = true;
      wsRef.current?.close();
    };
  }, [qc]);

  return status;
}