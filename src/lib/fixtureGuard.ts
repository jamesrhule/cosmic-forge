/**
 * P4-02: a build with `VITE_API_URL` reads no fixtures, on the client or in
 * SSR. `loadFixture` / `loadJsonlFixture` call this first; a service that
 * reaches a fixture in that mode is a bug, so fail loudly instead of showing
 * demo data as if it came from the API (R7).
 */
import { DATA_SOURCE } from "@/config/features";
import { ServiceError } from "@/types/domain";

/**
 * Static reference content (not data) that every build may read: the F1–F7
 * formula catalogue shown beside the equations. Nothing else under
 * `/fixtures/` is read when the app talks to the API.
 */
export const REFERENCE_PREFIXES: readonly string[] = ["formulas/"];

export function assertFixtureReadAllowed(path: string): void {
  if (DATA_SOURCE !== "api") return;
  if (REFERENCE_PREFIXES.some((p) => path.startsWith(p))) return;
  throw new ServiceError(
    "NOT_IMPLEMENTED",
    `Fixture ${path} is not read when VITE_API_URL is set; this view has no API source yet.`,
  );
}
