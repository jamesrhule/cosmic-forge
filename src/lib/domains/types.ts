/**
 * QCompass DomainPlugin contract (PROMPT 4 v2).
 *
 * Every domain registers a single `DomainPlugin` object exporting
 * its label, default route, fixture roots, audit-check IDs, and
 * a flag-gating predicate. The `DomainSwitcher` and any future
 * navigator consume the registry via {@link getDomainPlugin} /
 * {@link listDomainPlugins} (see `./registry`).
 *
 * The interface intentionally carries display strings + paths,
 * not React components. Each route module is responsible for its
 * own rendering; the registry is metadata only.
 */

import type { FEATURES } from "@/config/features";
import type { QcompassDomain } from "@/types/qcompass";

/**
 * Future-domain placeholders the `DomainSwitcher` renders as
 * disabled pills until their plugins land.
 */
export interface DomainPlaceholder {
  id: QcompassDomain;
  label: string;
  reason: string;
}

export interface DomainPlugin {
  /** Stable id; matches the qcompass.domains entry-point name. */
  id: QcompassDomain;

  /** Human-readable label rendered by the DomainSwitcher. */
  label: string;

  /** Compact label used in the top-nav pill. */
  shortLabel: string;

  /** Default landing route, e.g. `/` or `/domains/chemistry/configurator`. */
  route: string;

  /**
   * URL template for the manifest schema. The service layer
   * (`getManifestSchema`) reads this when `FEATURES.liveBackend`
   * is true; otherwise it falls back to `manifestSchemaFixture`.
   */
  manifestSchemaPath: string;

  /** Static fixture path used when `FEATURES.liveBackend` is false. */
  manifestSchemaFixture: string;

  /**
   * Root path under `/public/fixtures/` that holds run JSONs for
   * this domain.
   */
  fixturesRoot: string;

  /** Audit-check IDs (S1–S15 / S-chem-1..5 / etc.). */
  auditCheckIds: readonly string[];

  /** arXiv IDs the audit cites. */
  references: readonly string[];

  /**
   * Predicate that decides whether the plugin is rendered. The
   * `FEATURES` object is passed in so plugins can branch on
   * fine-grained flags. Cosmology returns `() => true`;
   * chemistry returns `(f) => f.qcompassMultiDomain`.
   */
  enabled: (flags: typeof FEATURES) => boolean;
}
