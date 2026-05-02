/**
 * QCompass — Manifest schema service.
 *
 * Returns the JSONSchema7 used by rjsf to render the configurator form
 * for a given domain. Today reads from `public/fixtures/<domain>/
 * manifest-schema.json`; tomorrow hits the live endpoint.
 *
 * @example
 *   const schema = await getManifestSchema("hep.lattice");
 */
import type { JSONSchema7 } from "json-schema";
import { FEATURES } from "@/config/features";
import { loadFixture } from "@/lib/fixtures";
import { getDomain } from "@/lib/domains/registry";
import type { DomainId } from "@/lib/domains/types";
import { apiFetch, isQcompassBackendConfigured } from "./http";

/** @endpoint GET /api/qcompass/domains/{domain}/schema */
export async function getManifestSchema(domain: DomainId): Promise<JSONSchema7> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<JSONSchema7>(
        `/api/qcompass/domains/${encodeURIComponent(domain)}/schema`,
      );
    } catch {
      /* fall through to fixture */
    }
  }
  const plugin = getDomain(domain);
  const path = plugin?.manifestSchemaUrl ?? `${domain}/manifest-schema.json`;
  return loadFixture<JSONSchema7>(path);
}
