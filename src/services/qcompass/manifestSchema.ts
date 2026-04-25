/**
 * Manifest schema loader.
 *
 * Returns the JSON Schema for a given QCompass domain so the
 * `JsonSchemaForm` component can render the configurator without
 * any per-domain hand-coding.
 */

import { FEATURES, API_BASE_URL } from "@/config/features";
import { loadFixture } from "@/lib/fixtures";
import {
  ServiceError,
} from "@/types/domain";
import type { JsonSchema, QcompassDomain } from "@/types/qcompass";

const FIXTURE_BY_DOMAIN: Partial<Record<QcompassDomain, string>> = {
  chemistry: "chemistry/manifest-schema.json",
};

/**
 * Resolve the manifest schema for a domain.
 *
 * Backend (when `FEATURES.liveBackend === true`):
 *   GET {API_BASE_URL}/api/qcompass/domains/{domain}/schema
 *
 * Otherwise: loads `/public/fixtures/{FIXTURE_BY_DOMAIN[domain]}`.
 */
export async function getManifestSchema(
  domain: QcompassDomain,
): Promise<JsonSchema> {
  if (FEATURES.liveBackend && API_BASE_URL) {
    const url = `${API_BASE_URL}/api/qcompass/domains/${domain}/schema`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new ServiceError(
        "UPSTREAM_FAILURE",
        `Manifest schema fetch failed: ${url} (status ${res.status})`,
      );
    }
    return (await res.json()) as JsonSchema;
  }
  const fixturePath = FIXTURE_BY_DOMAIN[domain];
  if (!fixturePath) {
    throw new ServiceError(
      "NOT_IMPLEMENTED",
      `No manifest-schema fixture for domain '${domain}'`,
    );
  }
  return loadFixture<JsonSchema>(fixturePath);
}
