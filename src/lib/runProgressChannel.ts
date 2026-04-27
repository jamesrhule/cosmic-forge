/**
 * Run-progress streaming — Tier 5 scaffold for "WebSocket streaming".
 *
 * Uses Supabase Realtime (a managed WebSocket transport) with a per-run
 * broadcast channel. The job worker emits frames via the service-role
 * client; the browser subscribes here. Realtime gives us auth, fan-out,
 * and reconnection for free, so we don't need to ship our own WS server.
 *
 * Channel topic: `run:<runId>`
 * Events:
 *   - "progress" -> { fraction: number, frame: number, status: string }
 *   - "log"      -> { line: string, level: "info" | "warn" | "error" }
 *   - "done"     -> { ok: boolean, error?: string }
 */

import { useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import type { RealtimeChannel } from "@supabase/supabase-js";

export interface RunProgressEvent {
  fraction: number;
  frame: number;
  status: string;
}

export interface RunLogEvent {
  line: string;
  level: "info" | "warn" | "error";
}

export interface RunDoneEvent {
  ok: boolean;
  error?: string;
}

export interface UseRunProgressState {
  progress: RunProgressEvent | null;
  lastLog: RunLogEvent | null;
  done: RunDoneEvent | null;
  connected: boolean;
}

export function useRunProgress(runId: string | null | undefined): UseRunProgressState {
  const [progress, setProgress] = useState<RunProgressEvent | null>(null);
  const [lastLog, setLastLog] = useState<RunLogEvent | null>(null);
  const [done, setDone] = useState<RunDoneEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const channelRef = useRef<RealtimeChannel | null>(null);

  useEffect(() => {
    if (!runId) return;
    const channel = supabase
      .channel(`run:${runId}`)
      .on("broadcast", { event: "progress" }, ({ payload }) => {
        setProgress(payload as RunProgressEvent);
      })
      .on("broadcast", { event: "log" }, ({ payload }) => {
        setLastLog(payload as RunLogEvent);
      })
      .on("broadcast", { event: "done" }, ({ payload }) => {
        setDone(payload as RunDoneEvent);
      })
      .subscribe((status) => {
        setConnected(status === "SUBSCRIBED");
      });
    channelRef.current = channel;
    return () => {
      supabase.removeChannel(channel);
      channelRef.current = null;
    };
  }, [runId]);

  return { progress, lastLog, done, connected };
}
