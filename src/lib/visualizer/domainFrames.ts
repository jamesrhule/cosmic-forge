/**
 * Normalise domain visualization frames into the canonical structured
 * types in `src/components/visualizer/panels/types.ts`.
 *
 * Accepts both wire shapes (structured and flat — see the types module)
 * and is the only place frames are reshaped. Quantities the source did
 * not provide stay `null` / empty; nothing is inferred or invented
 * (R6/R7). Only structural re-indexing happens here (array position →
 * `index`, bare `[x, y, z]` tuples → named coordinates).
 */
import type {
  AmoAtom,
  AmoBlockade,
  AmoCorrelations,
  ChemistryOrbital,
  ChemistrySlater,
  ChemistryTerm,
  CondmatBond,
  CondmatLatticeSite,
  CondmatOtoc,
  CondmatSpectral,
  DomainName,
  DomainTimelineResponse,
  DomainVisualizationFrame,
  HepPlaquette,
  NuclearLNV,
  NuclearModelDomain,
  NuclearShell,
  ParticleObservable,
  VisualizationFrame,
  VisualizationManifest,
} from "@/components/visualizer/panels/types";

type Raw = Record<string, unknown>;

const DOMAINS: ReadonlySet<DomainName> = new Set([
  "cosmology",
  "chemistry",
  "condmat",
  "hep",
  "nuclear",
  "amo",
  "gravity",
  "statmech",
]);

const NUCLEAR_MODEL_DOMAINS: ReadonlySet<string> = new Set([
  "1+1D_toy",
  "few_body_3d",
  "effective_hamiltonian",
]);

export function isDomainName(v: unknown): v is DomainName {
  return typeof v === "string" && DOMAINS.has(v as DomainName);
}

function isObj(v: unknown): v is Raw {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
function arr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}
function numOr(v: unknown, d: number): number {
  return num(v) ?? d;
}
function numArr(v: unknown): number[] {
  return arr(v).filter((x): x is number => typeof x === "number" && Number.isFinite(x));
}
function matrix(v: unknown): number[][] {
  return arr(v).map(numArr);
}
function indices(n: number): number[] {
  return Array.from({ length: n }, (_, i) => i);
}

function base(raw: Raw) {
  return {
    tau: numOr(raw.tau, 0),
    phase: typeof raw.phase === "string" ? raw.phase : "",
    active_terms: arr(raw.active_terms).filter((t): t is string => typeof t === "string"),
    provenance_ref: typeof raw.provenance_ref === "string" ? raw.provenance_ref : null,
  };
}

// ─── per-domain ────────────────────────────────────────────────────

function chemistryOrbitals(v: unknown): ChemistryOrbital[] {
  return arr(v).flatMap((o, i): ChemistryOrbital[] => {
    if (typeof o === "number") {
      return [{ index: i, occupation: o, energy_hartree: null, coefficients: [] }];
    }
    if (isObj(o)) {
      return [
        {
          index: numOr(o.index, i),
          occupation: numOr(o.occupation, 0),
          energy_hartree: num(o.energy_hartree),
          coefficients: numArr(o.coefficients),
        },
      ];
    }
    return [];
  });
}

function chemistrySlater(v: unknown): ChemistrySlater[] {
  return arr(v).flatMap((d): ChemistrySlater[] =>
    isObj(d) && typeof d.label === "string"
      ? [{ label: d.label, weight: numOr(d.weight, 0), occupations: numArr(d.occupations) }]
      : [],
  );
}

function chemistryTerms(v: unknown): ChemistryTerm[] {
  return arr(v).flatMap((t): ChemistryTerm[] =>
    isObj(t) && typeof t.label === "string"
      ? [
          {
            label: t.label,
            coefficient: numOr(t.coefficient, 0),
            operator: typeof t.operator === "string" ? t.operator : "",
          },
        ]
      : [],
  );
}

function condmatSites(v: unknown): CondmatLatticeSite[] {
  return arr(v).flatMap((s, i): CondmatLatticeSite[] => {
    if (Array.isArray(s)) {
      const [x, y, z] = s;
      return [{ index: i, x: numOr(x, 0), y: numOr(y, 0), z: numOr(z, 0), spin: null }];
    }
    if (isObj(s)) {
      return [
        {
          index: numOr(s.index, i),
          x: numOr(s.x, 0),
          y: numOr(s.y, 0),
          z: numOr(s.z, 0),
          spin: num(s.spin),
        },
      ];
    }
    return [];
  });
}

function condmatBonds(v: unknown): { paired: CondmatBond[]; unpaired: number[] } {
  const paired: CondmatBond[] = [];
  const unpaired: number[] = [];
  for (const b of arr(v)) {
    if (typeof b === "number" && Number.isFinite(b)) unpaired.push(b);
    else if (isObj(b) && num(b.a) !== null && num(b.b) !== null) {
      paired.push({ a: b.a as number, b: b.b as number, strength: numOr(b.strength, 0) });
    }
  }
  return { paired, unpaired };
}

function condmatOtoc(raw: Raw): CondmatOtoc | null {
  const rich = raw.otoc_butterfly;
  if (isObj(rich)) {
    return {
      times: numArr(rich.times),
      distances: numArr(rich.distances),
      intensity: matrix(rich.intensity),
      axes: "physical",
    };
  }
  const flat = matrix(raw.otoc);
  if (flat.length === 0) return null;
  return {
    times: indices(flat.length),
    distances: indices(flat[0]?.length ?? 0),
    intensity: flat,
    axes: "index",
  };
}

function condmatSpectral(raw: Raw): CondmatSpectral | null {
  const rich = raw.spectral_function_Akw;
  if (isObj(rich)) {
    return {
      omega: numArr(rich.omega),
      k: numArr(rich.k),
      Akw: matrix(rich.Akw),
      axes: "physical",
    };
  }
  const flat = matrix(raw.spectral);
  if (flat.length === 0) return null;
  return {
    k: indices(flat.length),
    omega: indices(flat[0]?.length ?? 0),
    Akw: flat,
    axes: "index",
  };
}

function hepPlaquettes(v: unknown): HepPlaquette[] {
  return arr(v).flatMap((p, i): HepPlaquette[] => {
    if (typeof p === "number") return [{ cell: [i, 0, 0], flux: null, energy: p }];
    if (isObj(p)) {
      const c = numArr(p.cell);
      return [
        { cell: [c[0] ?? i, c[1] ?? 0, c[2] ?? 0], flux: num(p.flux), energy: num(p.energy) },
      ];
    }
    return [];
  });
}

function particleObs(v: unknown): Record<string, ParticleObservable> {
  if (!isObj(v)) return {};
  const out: Record<string, ParticleObservable> = {};
  for (const [k, o] of Object.entries(v)) {
    // Keys come from run payloads; refuse prototype-polluting names.
    if (!isObj(o) || k === "__proto__" || k === "constructor" || k === "prototype") continue;
    out[k] = {
      value: num(o.value),
      unit: typeof o.unit === "string" ? o.unit : "",
      uncertainty: num(o.uncertainty),
      status: typeof o.status === "string" ? o.status : "unavailable",
      notes: typeof o.notes === "string" ? o.notes : "",
    };
  }
  return out;
}

function nuclearShells(v: unknown): NuclearShell[] {
  return arr(v).flatMap((s, i): NuclearShell[] => {
    if (typeof s === "number") return [{ shell: String(i), n: s, energy_MeV: null }];
    if (isObj(s)) {
      return [
        {
          shell: typeof s.shell === "string" ? s.shell : String(i),
          n: numOr(s.n, 0),
          energy_MeV: num(s.energy_MeV),
        },
      ];
    }
    return [];
  });
}

function nuclearLnv(v: unknown): NuclearLNV | null {
  if (!isObj(v)) return null;
  return { delta_L: numOr(v.delta_L, 0), delta_B: numOr(v.delta_B, 0), rate: numOr(v.rate, 0) };
}

function amoAtoms(v: unknown): AmoAtom[] {
  return arr(v).flatMap((a, i): AmoAtom[] => {
    if (Array.isArray(a)) {
      const [x, y, z] = a;
      return [{ index: i, x: numOr(x, 0), y: numOr(y, 0), z: numOr(z, 0), rydberg: null }];
    }
    if (isObj(a)) {
      return [
        {
          index: numOr(a.index, i),
          x: numOr(a.x, 0),
          y: numOr(a.y, 0),
          z: numOr(a.z, 0),
          rydberg: typeof a.rydberg === "boolean" ? a.rydberg : null,
        },
      ];
    }
    return [];
  });
}

function amoBlockade(v: unknown): AmoBlockade[] {
  return arr(v).flatMap((b, i): AmoBlockade[] => {
    if (typeof b === "number") return [{ atom: i, r_blockade: b }];
    if (isObj(b)) return [{ atom: numOr(b.atom, i), r_blockade: numOr(b.r_blockade, 0) }];
    return [];
  });
}

function amoCorrelations(v: unknown): AmoCorrelations | null {
  if (!isObj(v)) return null;
  const pairs = arr(v.pairs).flatMap((p): [number, number][] => {
    const q = numArr(p);
    return q.length === 2 ? [[q[0], q[1]]] : [];
  });
  return { pairs, g2: numArr(v.g2) };
}

/** Lift one raw frame (either wire shape) into the canonical type. */
export function normalizeDomainFrame(
  raw: unknown,
  fallbackDomain?: DomainName,
): VisualizationFrame | null {
  if (!isObj(raw)) return null;
  const domain = isDomainName(raw.domain) ? raw.domain : fallbackDomain;
  if (!domain) return null;
  const b = base(raw);
  switch (domain) {
    case "cosmology": {
      const modes = isObj(raw.modes) ? raw.modes : {};
      return {
        ...b,
        domain,
        modes: {
          k: numArr(modes.k),
          omega_re: numArr(modes.omega_re),
          omega_im: numArr(modes.omega_im),
        },
        B_plus: numArr(raw.B_plus),
        B_minus: numArr(raw.B_minus),
        sgwb: numArr(raw.sgwb),
        anomaly: numOr(raw.anomaly, 0),
        lepton_flow: numOr(raw.lepton_flow, 0),
      };
    }
    case "chemistry":
      return {
        ...b,
        domain,
        iteration: num(raw.iteration),
        orbitals: chemistryOrbitals(raw.orbitals),
        energy_convergence: numArr(raw.energy_convergence),
        slater_determinants: chemistrySlater(raw.slater_determinants),
        slater_flow: matrix(raw.slater),
        hamiltonian_terms: chemistryTerms(raw.hamiltonian_terms),
      };
    case "condmat": {
      const bonds = condmatBonds(raw.bond_strengths);
      return {
        ...b,
        domain,
        lattice_sites: condmatSites(raw.lattice_sites),
        bond_strengths: bonds.paired,
        unpaired_bond_strengths: bonds.unpaired,
        otoc_butterfly: condmatOtoc(raw),
        spectral_function_Akw: condmatSpectral(raw),
      };
    }
    case "hep":
      return {
        ...b,
        domain,
        plaquettes: hepPlaquettes(raw.plaquettes),
        chiral_condensate: numOr(raw.chiral_condensate, 0),
        string_tension: numOr(raw.string_tension, 0),
        particle_obs: particleObs(raw.particle_obs),
      };
    case "nuclear":
      return {
        ...b,
        domain,
        shell_occupation: nuclearShells(raw.shell_occupation),
        lnv_tracker: nuclearLnv(raw.lnv_tracker),
        lnv_indicator: num(raw.lnv_tracker) ?? num(raw.lnv_indicator),
        model_domain:
          typeof raw.model_domain === "string" && NUCLEAR_MODEL_DOMAINS.has(raw.model_domain)
            ? (raw.model_domain as NuclearModelDomain)
            : null,
      };
    case "amo":
      return {
        ...b,
        domain,
        atom_positions: amoAtoms(raw.atom_positions),
        blockade_radii: amoBlockade(raw.blockade_radii),
        correlations: amoCorrelations(raw.correlations),
        // A bare matrix is the flat shape's ⟨σᶻσᶻ⟩ — a different
        // observable from g², so it is kept apart, not relabelled.
        zz_correlations: Array.isArray(raw.correlations) ? matrix(raw.correlations) : [],
      };
    case "gravity":
      return {
        ...b,
        domain,
        spectrum: numArr(raw.spectrum),
        spectral_form_factor: numArr(raw.spectral_form_factor),
        is_learned_hamiltonian: raw.is_learned_hamiltonian === true,
        provenance_warning:
          typeof raw.provenance_warning === "string" ? raw.provenance_warning : null,
        model_domain:
          raw.model_domain === "JT_matrix_model" || raw.model_domain === "SYK_sparse"
            ? raw.model_domain
            : "toy_SYK_1+1D",
      };
    case "statmech":
      return {
        ...b,
        domain,
        estimate: numOr(raw.estimate, 0),
        sigma: numOr(raw.sigma, 0),
        truth: num(raw.truth),
        history: numArr(raw.history),
      };
  }
}

/**
 * Normalise a timeline envelope. Accepts `{manifest, frames}`
 * (structured) or `{run_id, domain, frames}` (flat). `synthetic` marks
 * fixture-sourced data so the UI labels it (R7).
 */
export function normalizeDomainTimeline(
  raw: unknown,
  fallback: { run_id: string; domain: DomainName; synthetic?: boolean },
): DomainTimelineResponse {
  const r = isObj(raw) ? raw : {};
  const domain = isDomainName(r.domain) ? r.domain : fallback.domain;
  const frames = arr(r.frames)
    .map((f) => normalizeDomainFrame(f, domain))
    .filter((f): f is DomainVisualizationFrame => f !== null && f.domain !== "cosmology");
  const m = isObj(r.manifest) ? r.manifest : null;
  const metadata = isObj(m?.metadata) ? { ...(m?.metadata as Raw) } : {};
  if (fallback.synthetic || r.synthetic === true) metadata.synthetic = true;
  const manifest: VisualizationManifest = {
    run_id:
      typeof m?.run_id === "string"
        ? m.run_id
        : typeof r.run_id === "string"
          ? r.run_id
          : fallback.run_id,
    domain: m && isDomainName(m.domain) ? m.domain : domain,
    frame_count: num(m?.frame_count) ?? frames.length,
    formula_variant: typeof m?.formula_variant === "string" ? m.formula_variant : null,
    bake_uri: typeof m?.bake_uri === "string" ? m.bake_uri : null,
    metadata,
  };
  return { manifest, frames };
}

/**
 * Domains the `cosmic_forge_viz` server does not serve on `/api/runs`
 * and `/ws/runs`; they are only on the M8 `/api/qcompass` and
 * `/ws/qcompass` routes, keyed by registry domain id.
 */
export const QCOMPASS_ONLY_DOMAINS: Readonly<Partial<Record<DomainName, string>>> = {
  gravity: "gravity.syk",
  statmech: "statmech.sampling",
};

/** REST / WS / SSE paths for a domain timeline (P0-02 viz protocol). */
export function domainVisualizationPath(
  kind: "api" | "ws" | "sse",
  domain: DomainName,
  runId: string,
): string | null {
  const id = encodeURIComponent(runId);
  const m8 = QCOMPASS_ONLY_DOMAINS[domain];
  if (m8) {
    if (kind === "sse") return null; // no SSE route for these domains
    return `/${kind}/qcompass/domains/${encodeURIComponent(m8)}/runs/${id}/visualization`;
  }
  return `/${kind}/runs/${domain}/${id}/visualization`;
}

/**
 * One message of the viz stream protocol: every WS message (and the
 * SSE `header` event) is an envelope `{type, seq, tau, payload}` with
 * `type` ∈ header | frame | end | error. Returns the frame for `frame`
 * envelopes, `"end"` for end/error, `null` to skip.
 */
export function unwrapStreamEnvelope(
  msg: unknown,
  domain: DomainName,
): DomainVisualizationFrame | "end" | null {
  if (!isObj(msg)) return null;
  if (msg.type === "end" || msg.type === "error") return "end";
  if (msg.type === "header") return null;
  const raw = msg.type === "frame" ? msg.payload : msg;
  // Frames always carry τ; header-shaped payloads never do.
  if (!isObj(raw) || typeof raw.tau !== "number") return null;
  const f = normalizeDomainFrame(raw, domain);
  return f && f.domain !== "cosmology" ? f : null;
}
