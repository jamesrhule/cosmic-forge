/**
 * Chemistry DomainPlugin (PROMPT 4 v2).
 *
 * Wraps the existing chemistry routes + fixtures from PROMPT 4 v1
 * (commit 57c2e43). The plugin is gated behind
 * `FEATURES.qcompassMultiDomain` so deep-linking to
 * `/domains/chemistry/*` returns a "feature off" notice when the
 * flag is false; the cosmology view is byte-identical at default.
 */

import type { DomainPlugin } from "./types";

export const chemistry: DomainPlugin = {
  id: "chemistry",
  label: "Chemistry",
  shortLabel: "Chemistry",
  route: "/domains/chemistry/configurator",
  manifestSchemaPath: "/api/qcompass/domains/chemistry/schema",
  manifestSchemaFixture: "chemistry/manifest-schema.json",
  fixturesRoot: "/fixtures/chemistry/runs",
  auditCheckIds: [
    "S-chem-1", "S-chem-2", "S-chem-3", "S-chem-4", "S-chem-5",
  ] as const,
  // S-chem-1 cites the H2/STO-3G FCI textbook value; S-chem-3
  // cites NIST CCCBDB; S-chem-4 cites the Quantum-Echoes /
  // qiskit-addon-sqd reference. The list below is a subset of
  // the bibliography the bench manifests carry in their
  // `references` field.
  references: ["10.1007/978-3-319-16729-9", "2401.04188"] as const,
  enabled: (flags) => Boolean(flags.qcompassMultiDomain),
};
