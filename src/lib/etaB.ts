/**
 * How a run's η_B reads to a user (display only, R6).
 *
 * The engine refuses to publish η_B under its precision policy
 * (`ucgle_f1.m7_infer.pipeline.eta_B_refusal`): `RunResult.eta_B.value` is
 * then NaN, which arrives as `null` (FastAPI JSON) or as the stored marker
 * `"NaN"` (the platform route, P3-03), with the reason in `eta_B.refusal`.
 * A refused η_B is never shown as a number; it reads
 * "η_B not published — <reason>". Bundled fixtures carry a finite value and
 * no `refusal`, so they read exactly as before.
 */

export type EtaBReading =
  | { kind: "published"; value: number }
  | { kind: "refused"; reason: string };

/** Shown when a non-finite η_B carries no reason (results stored before `refusal`). */
export const ETA_B_NO_REASON = "no finite value was returned (reason not recorded)";

export function readEtaB(eta: unknown): EtaBReading | null {
  if (!eta || typeof eta !== "object") return null;
  const { value, refusal } = eta as { value?: unknown; refusal?: unknown };
  if (typeof refusal === "string" && refusal.trim() !== "") {
    return { kind: "refused", reason: refusal.trim() };
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return { kind: "published", value };
  }
  if (value === undefined && refusal === undefined) return null;
  return { kind: "refused", reason: ETA_B_NO_REASON };
}

/** The exact text for a refused η_B. */
export function etaBNotPublished(reason: string): string {
  return `η_B not published — ${reason}`;
}
