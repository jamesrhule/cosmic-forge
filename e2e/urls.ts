/**
 * The two production Worker builds `scripts/e2e_serve.sh` serves (P0-06).
 * Specs for the QCompass domains run against DOMAINS_URL (all
 * VITE_QCOMPASS_* flags on); everything else uses the default build, which is
 * what users get with no flags.
 */
export const DEFAULT_URL = `http://127.0.0.1:${process.env.E2E_PORT_DEFAULT ?? "4310"}`;
export const DOMAINS_URL = `http://127.0.0.1:${process.env.E2E_PORT_DOMAINS ?? "4311"}`;
