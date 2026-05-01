/**
 * QCompass DomainPlugin registry (PROMPT 4 v2).
 *
 * The frontend's source of truth for "what domains exist and how
 * are they labelled". The DomainSwitcher and any future navigator
 * consume this rather than hard-coding domain strings.
 *
 * Adding a new domain is a one-line registration: drop a sibling
 * file (`condmat.ts`, `hep.ts`, …) implementing `DomainPlugin`,
 * import it here, and append to the `_REGISTRY` array.
 */

import { FEATURES } from "@/config/features";
import { chemistry } from "./chemistry";
import { cosmologyUcglef1 } from "./cosmology.ucglef1";
import type { DomainPlaceholder, DomainPlugin } from "./types";

const _REGISTRY: ReadonlyArray<DomainPlugin> = [
  cosmologyUcglef1,
  chemistry,
];

/**
 * Disabled future domains the DomainSwitcher renders as greyed
 * pills. Each entry has an `id` (so type-checking against
 * `QcompassDomain` succeeds), a label, and a one-line "why".
 *
 * The registry never returns these from {@link listDomainPlugins}
 * — they are display-only metadata.
 */
export const PHASE2_PLACEHOLDERS: ReadonlyArray<DomainPlaceholder> = [
  { id: "condmat", label: "Condensed matter", reason: "qfull-condmat plugin landed; UI integration pending." },
  { id: "hep", label: "High-energy phenomenology", reason: "qfull-hep plugin landed; UI integration pending." },
  { id: "nuclear", label: "Nuclear", reason: "qfull-nuclear plugin landed; UI integration pending." },
  { id: "amo", label: "Atomic / molecular / optical", reason: "qfull-amo plugin landed; UI integration pending." },
  { id: "gravity", label: "Gravity (templates / NR)", reason: "qfull-gravity placeholder only." },
  { id: "statmech", label: "Statistical mechanics", reason: "qfull-statmech placeholder only." },
];

/** Return every registered plugin (filtered by current FEATURES gates). */
export function listDomainPlugins(
  flags: typeof FEATURES = FEATURES,
): ReadonlyArray<DomainPlugin> {
  return _REGISTRY.filter((plugin) => plugin.enabled(flags));
}

/** Return every registered plugin regardless of feature flags. */
export function listAllDomainPlugins(): ReadonlyArray<DomainPlugin> {
  return _REGISTRY;
}

/** Look up a plugin by its `id`. */
export function getDomainPlugin(id: DomainPlugin["id"]): DomainPlugin {
  const found = _REGISTRY.find((plugin) => plugin.id === id);
  if (!found) {
    const known = _REGISTRY.map((p) => p.id).join(", ");
    throw new Error(
      `No DomainPlugin registered for id="${id}". Known ids: ${known}.`,
    );
  }
  return found;
}
