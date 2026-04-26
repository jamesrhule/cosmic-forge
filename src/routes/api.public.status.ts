/**
 * Public health endpoint used by `/status` and any external uptime
 * monitor. Anonymous-readable, never returns PII, never bypasses RLS.
 *
 * Response shape:
 *   {
 *     ok: boolean,
 *     build: { commit, builtAt },
 *     checks: { database: ProbeResult, storage: ProbeResult },
 *     incidents: { open: number, latest: IncidentSummary | null },
 *     timestamp: string,
 *   }
 *
 * Each probe runs against the anon supabase client so we measure the
 * exact path real users hit. Probe failures NEVER throw — they downgrade
 * to `{ ok: false, message }` so the JSON shape is stable regardless of
 * upstream state.
 */

import { createFileRoute } from "@tanstack/react-router";
import { createClient } from "@supabase/supabase-js";
import type { Database } from "@/integrations/supabase/types";

interface ProbeResult {
  ok: boolean;
  latencyMs: number;
  message?: string;
}

interface IncidentSummary {
  id: string;
  title: string;
  status: string;
  severity: string;
  startedAt: string;
  resolvedAt: string | null;
}

const PROBE_TIMEOUT_MS = 4000;

async function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return await Promise.race([
    p,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`probe timed out after ${ms}ms`)), ms),
    ),
  ]);
}

export const Route = createFileRoute("/api/public/status")({
  server: {
    handlers: {
      GET: async () => {
        const SUPABASE_URL = process.env.SUPABASE_URL;
        const SUPABASE_PUBLISHABLE_KEY = process.env.SUPABASE_PUBLISHABLE_KEY;

        const build = {
          commit: typeof __APP_COMMIT__ !== "undefined" ? __APP_COMMIT__ : "unknown",
          builtAt: typeof __APP_BUILD_DATE__ !== "undefined" ? __APP_BUILD_DATE__ : "unknown",
        };

        if (!SUPABASE_URL || !SUPABASE_PUBLISHABLE_KEY) {
          return Response.json(
            {
              ok: false,
              build,
              checks: {
                database: { ok: false, latencyMs: 0, message: "supabase env not configured" },
                storage: { ok: false, latencyMs: 0, message: "supabase env not configured" },
              },
              incidents: { open: 0, latest: null },
              timestamp: new Date().toISOString(),
            },
            { status: 503, headers: { "Cache-Control": "no-store" } },
          );
        }

        const supabase = createClient<Database>(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
          auth: { storage: undefined, persistSession: false, autoRefreshToken: false },
        });

        // Probe 1: database — public read on a tiny table.
        const dbStart = performance.now();
        let database: ProbeResult;
        try {
          const { error } = await withTimeout(
            Promise.resolve(
              supabase.from("system_incidents").select("id", { count: "exact", head: true }),
            ),
            PROBE_TIMEOUT_MS,
          );
          database = error
            ? { ok: false, latencyMs: Math.round(performance.now() - dbStart), message: error.message }
            : { ok: true, latencyMs: Math.round(performance.now() - dbStart) };
        } catch (err) {
          database = {
            ok: false,
            latencyMs: Math.round(performance.now() - dbStart),
            message: err instanceof Error ? err.message : String(err),
          };
        }

        // Probe 2: storage — list one file from a known bucket.
        const stStart = performance.now();
        let storage: ProbeResult;
        try {
          const { error } = await withTimeout(
            supabase.storage.from("viz-timelines").list("", { limit: 1 }),
            PROBE_TIMEOUT_MS,
          );
          storage = error
            ? { ok: false, latencyMs: Math.round(performance.now() - stStart), message: error.message }
            : { ok: true, latencyMs: Math.round(performance.now() - stStart) };
        } catch (err) {
          storage = {
            ok: false,
            latencyMs: Math.round(performance.now() - stStart),
            message: err instanceof Error ? err.message : String(err),
          };
        }

        // Open incidents (bounded; we don't leak the full table).
        let incidents = { open: 0, latest: null as IncidentSummary | null };
        try {
          const { data } = await withTimeout(
            supabase
              .from("system_incidents")
              .select("id,title,status,severity,started_at,resolved_at")
              .neq("status", "resolved")
              .order("started_at", { ascending: false })
              .limit(5),
            PROBE_TIMEOUT_MS,
          );
          if (Array.isArray(data) && data.length > 0) {
            const top = data[0];
            incidents = {
              open: data.length,
              latest: {
                id: top.id,
                title: top.title,
                status: top.status,
                severity: top.severity,
                startedAt: top.started_at,
                resolvedAt: top.resolved_at,
              },
            };
          }
        } catch {
          // probe failure is non-fatal; status page still renders.
        }

        const ok = database.ok && storage.ok && incidents.open === 0;
        return Response.json(
          {
            ok,
            build,
            checks: { database, storage },
            incidents,
            timestamp: new Date().toISOString(),
          },
          {
            status: ok ? 200 : 503,
            headers: {
              "Cache-Control": "public, max-age=10, s-maxage=10",
              "Access-Control-Allow-Origin": "*",
            },
          },
        );
      },
    },
  },
});
