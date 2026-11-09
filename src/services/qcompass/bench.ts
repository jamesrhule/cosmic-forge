/**
 * QCompass — Bench suite service (research views).
 *
 * The particle suite's cross-domain leaderboard is a bundled fixture until
 * the bench leaderboard is served live (P2-14). With `VITE_API_URL` set the
 * app reads no fixtures (P4-02), so this reports that the leaderboard has no
 * API source yet instead of showing demo rows as if they were live.
 */
import { loadFixture } from "@/lib/fixtures";
import { usesApi } from "@/lib/sdk";
import { ServiceError } from "@/types/domain";

export interface SuiteRow {
  domain: string;
  run_id: string;
  observable: string;
  value: number;
  uncertainty: number;
  reference_value: number;
  sigma: number;
}

export interface SuitePayload {
  suite: string;
  generated_at: string;
  rows: SuiteRow[];
}

export async function getParticleSuite(): Promise<SuitePayload> {
  if (usesApi()) {
    throw new ServiceError(
      "NOT_IMPLEMENTED",
      "The bench leaderboard is not served by the compute API yet (P2-14).",
    );
  }
  return loadFixture<SuitePayload>("benchmarks/particle-suite.json");
}
