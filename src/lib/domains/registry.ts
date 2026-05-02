/**
 * QCompass — Domain registry (in-memory, populated at module load).
 *
 * Phase 1 ships exactly one ALWAYS-ENABLED domain (`cosmology.ucglef1`).
 * Seven additional domains self-register via `register-all.ts`. Each
 * is gated by `FEATURES.qcompassMultiDomain && FEATURES.qcompass<X>`.
 *
 * When the master flag is OFF, `listDomainSurface()` returns only
 * cosmology, matching the pre-QCompass build exactly.
 *
 * Isolation rule: do NOT import this from anything under
 * `src/services/`. The registry wraps services; services do not know
 * the registry exists.
 */

import { FEATURES } from "@/config/features";
import type { DomainId, DomainPlugin } from "./types";

const REGISTRY = new Map<DomainId, DomainPlugin<unknown, unknown>>();

export function registerDomain<TProblem, TResult>(
  plugin: DomainPlugin<TProblem, TResult>,
): void {
  REGISTRY.set(plugin.id, plugin as DomainPlugin<unknown, unknown>);
}

export function getDomain(id: DomainId): DomainPlugin<unknown, unknown> | undefined {
  const plugin = REGISTRY.get(id);
  if (!plugin) return undefined;
  // Cosmology is unconditional. Any other domain is hidden when the
  // master multi-domain flag is off, even if its individual flag is on.
  if (plugin.id !== "cosmology.ucglef1" && !FEATURES.qcompassMultiDomain) {
    return undefined;
  }
  return plugin;
}

export function listDomains(): DomainPlugin<unknown, unknown>[] {
  const all = Array.from(REGISTRY.values());
  if (FEATURES.qcompassMultiDomain) return all;
  return all.filter((p) => p.id === "cosmology.ucglef1");
}

export function listDomainSurface(): Array<{
  id: DomainId;
  label: string;
  description: string;
  enabled: boolean;
  disabledReason?: string;
  capability: DomainPlugin["capability"];
}> {
  return listDomains().map((p) => ({
    id: p.id,
    label: p.label,
    description: p.description,
    enabled: p.enabled,
    disabledReason: p.disabledReason,
    capability: p.capability,
  }));
}
