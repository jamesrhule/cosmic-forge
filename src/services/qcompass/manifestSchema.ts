/**
 * QCompass — Manifest schema service.
 *
 * Returns the JSONSchema7 used by rjsf to render the configurator form
 * for a given domain: the domain plugin's schema from the compute API when
 * `VITE_API_URL` is set (P4-02), else `public/fixtures/<domain>/
 * manifest-schema.json`.
 *
 * @example
 *   const schema = await getManifestSchema("hep.lattice");
 */
import type { JSONSchema7 } from "json-schema";
import * as sdk from "@qcompass/frontend-sdk";
import { loadFixture } from "@/lib/fixtures";
import { api, usesApi } from "@/lib/sdk";
import { getDomain } from "@/lib/domains/registry";
import type { DomainId } from "@/lib/domains/types";

/** @endpoint GET /api/qcompass/domains/{domain}/schema */
export async function getManifestSchema(domain: DomainId): Promise<JSONSchema7> {
  if (usesApi()) {
    return (await api((c) => sdk.getDomainSchema(c, domain))) as JSONSchema7;
  }
  const plugin = getDomain(domain);
  const path = plugin?.manifestSchemaUrl ?? `${domain}/manifest-schema.json`;
  return loadFixture<JSONSchema7>(path);
}
