/**
 * QCompass — Domain registry (in-memory, populated at module load).
 *
 * Phase 1 ships exactly one registered domain (`cosmology.ucglef1`).
 * The other seven `DomainId` values surface in the UI as disabled
 * placeholders so the seam is visible but inert.
 *
 * Isolation rule: do NOT import this from anything under
 * `src/services/`. The registry wraps services; services do not know
 * the registry exists.
 */

import type { DomainId, DomainPlugin } from "./types";

const REGISTRY = new Map<DomainId, DomainPlugin<unknown, unknown>>();

export function registerDomain<TProblem, TResult>(
  plugin: DomainPlugin<TProblem, TResult>,
): void {
  REGISTRY.set(plugin.id, plugin as DomainPlugin<unknown, unknown>);
}

export function getDomain(id: DomainId): DomainPlugin<unknown, unknown> | undefined {
  return REGISTRY.get(id);
}

export function listDomains(): DomainPlugin<unknown, unknown>[] {
  return Array.from(REGISTRY.values());
}

/**
 * Phase 2 placeholders — show up disabled in the domain selector with
 * a "Phase 2" tooltip so users can see the surface area without being
 * able to invoke anything.
 */
const PHASE2_PLACEHOLDERS: Array<
  Pick<DomainPlugin, "id" | "label" | "description" | "capability"> & {
    disabledReason: string;
  }
> = [
  {
    id: "chemistry.molecular",
    label: "Chemistry · Molecular",
    description: "Strongly correlated transition-metal catalysis (FeMoco / P450 class).",
    capability: { classical: false, quantum: false, audited: false },
    disabledReason: "Phase 2 — early-FT target",
  },
  {
    id: "condmat.lattice",
    label: "Condensed Matter · Lattice",
    description: "2D Hubbard dynamics, frustrated magnets, spectral functions.",
    capability: { classical: false, quantum: false, audited: false },
    disabledReason: "Phase 2 — TN/QPU hybrid",
  },
  {
    id: "hep.lattice",
    label: "HEP · Lattice",
    description: "Real-time 1+1D Schwinger and 2+1D abelian gauge theories.",
    capability: { classical: false, quantum: false, audited: false },
    disabledReason: "Phase 2 — SC-ADAPT-VQE template",
  },
  {
    id: "nuclear.structure",
    label: "Nuclear · Structure",
    description: "Few-body NCSM and 1+1D 0νββ toy.",
    capability: { classical: false, quantum: false, audited: false },
    disabledReason: "Phase 2 — IonQ Forte template",
  },
  {
    id: "amo.rydberg",
    label: "AMO · Rydberg",
    description: "Neutral-atom analog quantum simulation (QuEra / Pasqal).",
    capability: { classical: false, quantum: false, audited: false },
    disabledReason: "Phase 2 — Bloqade integration",
  },
  {
    id: "gravity.syk",
    label: "Gravity · SYK / JT",
    description: "Sparsified SYK and JT dynamics — provenance-flagged toy models.",
    capability: { classical: false, quantum: false, audited: false },
    disabledReason: "Phase 3 — research only",
  },
  {
    id: "statmech.sampling",
    label: "Stat Mech · Sampling",
    description: "QAE, quantum Metropolis, thermofield-double preparation.",
    capability: { classical: false, quantum: false, audited: false },
    disabledReason: "Phase 3 — polynomial speedup target",
  },
];

export function listDomainSurface(): Array<{
  id: DomainId;
  label: string;
  description: string;
  enabled: boolean;
  disabledReason?: string;
  capability: DomainPlugin["capability"];
}> {
  const registered = listDomains();
  const registeredIds = new Set(registered.map((p) => p.id));

  const fromRegistered = registered.map((p) => ({
    id: p.id,
    label: p.label,
    description: p.description,
    enabled: p.enabled,
    disabledReason: p.disabledReason,
    capability: p.capability,
  }));

  const placeholders = PHASE2_PLACEHOLDERS.filter((p) => !registeredIds.has(p.id)).map(
    (p) => ({
      id: p.id,
      label: p.label,
      description: p.description,
      enabled: false,
      disabledReason: p.disabledReason,
      capability: p.capability,
    }),
  );

  return [...fromRegistered, ...placeholders];
}
