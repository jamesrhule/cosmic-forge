/**
 * QCompass — M15 Benchmark Suite (Phase 1 stub).
 *
 * Phase 1 re-exposes the existing UCGLE-F1 benchmarks tagged with
 * `domain: "cosmology.ucglef1"`. Phase 2 will add MQT Bench, SupermarQ,
 * QED-C, QASMBench adapters under the same interface.
 */

import { getBenchmarks } from "@/services/simulator";
import type { DomainId } from "@/lib/domains/types";
import type { BenchmarkEntry } from "@/types/domain";

export interface DomainBenchmarkEntry {
  domain: DomainId;
  entry: BenchmarkEntry;
}

export async function listBenchmarksForDomain(
  domain: DomainId,
): Promise<DomainBenchmarkEntry[]> {
  if (domain === "cosmology.ucglef1") {
    const index = await getBenchmarks();
    return index.benchmarks.map((entry) => ({ domain, entry }));
  }
  return [];
}
