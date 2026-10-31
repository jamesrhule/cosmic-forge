/**
 * Manifest + domain-timeline service.
 *
 * Wraps `apiFetch` with a small localStorage TTL cache so the route
 * loader can avoid re-fetching the manifest on every back-forward
 * navigation. Cache TTL is 5 minutes; clear via `clearManifestCache()`.
 */

import { apiFetch, BackendUnavailable } from "@/lib/apiClient";
import type {
  DomainTimelineResponse,
  VisualizationDomain,
  VisualizationManifest,
} from "@/types/manifest";

const CACHE_PREFIX = "cf:manifest:";
const CACHE_TTL_MS = 5 * 60 * 1000;

interface CacheEntry<T> {
  v: T;
  t: number;
}

function readCache<T>(key: string): T | null {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem(`${CACHE_PREFIX}${key}`);
    if (!raw) return null;
    const entry = JSON.parse(raw) as CacheEntry<T>;
    if (Date.now() - entry.t > CACHE_TTL_MS) {
      localStorage.removeItem(`${CACHE_PREFIX}${key}`);
      return null;
    }
    return entry.v;
  } catch {
    return null;
  }
}

function writeCache<T>(key: string, value: T): void {
  if (typeof localStorage === "undefined") return;
  try {
    const entry: CacheEntry<T> = { v: value, t: Date.now() };
    localStorage.setItem(`${CACHE_PREFIX}${key}`, JSON.stringify(entry));
  } catch {
    /* localStorage full or denied — silently skip */
  }
}

export async function getManifest(
  domain: VisualizationDomain,
  runId: string,
): Promise<VisualizationManifest> {
  const key = `${domain}:${runId}`;
  const cached = readCache<VisualizationManifest>(key);
  if (cached) return cached;

  try {
    const fresh = await apiFetch<VisualizationManifest>(
      `/api/runs/${domain}/${encodeURIComponent(runId)}/manifest`,
    );
    writeCache(key, fresh);
    return fresh;
  } catch (err) {
    if (err instanceof BackendUnavailable) {
      // Stand-in manifest so the route can still render against
      // bundled fixtures during local dev without a backend.
      return {
        run_id: runId,
        domain,
        frame_count: 60,
        formula_variant: null,
        bake_uri: null,
        metadata: { synthetic: true, source: "frontend-fallback" },
      };
    }
    throw err;
  }
}

export async function getDomainTimeline(
  domain: VisualizationDomain,
  runId: string,
  opts: { totalFrames?: number; maxFrames?: number } = {},
): Promise<DomainTimelineResponse> {
  const params = new URLSearchParams();
  if (opts.totalFrames !== undefined) params.set("total", String(opts.totalFrames));
  if (opts.maxFrames !== undefined) params.set("max_frames", String(opts.maxFrames));
  const query = params.toString();
  const path = `/api/runs/${domain}/${encodeURIComponent(runId)}/visualization${
    query ? `?${query}` : ""
  }`;
  try {
    return await apiFetch<DomainTimelineResponse>(path);
  } catch (err) {
    if (err instanceof BackendUnavailable) {
      // Surface an empty timeline rather than throwing; the lazy
      // component renders a banner explaining the backend is offline.
      const manifest = await getManifest(domain, runId);
      return { manifest, frames: [] };
    }
    throw err;
  }
}

export function clearManifestCache(): void {
  if (typeof localStorage === "undefined") return;
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const k = localStorage.key(i);
    if (k && k.startsWith(CACHE_PREFIX)) localStorage.removeItem(k);
  }
}

export function manifestCacheKey(
  domain: VisualizationDomain,
  runId: string,
): string {
  return `${CACHE_PREFIX}${domain}:${runId}`;
}
