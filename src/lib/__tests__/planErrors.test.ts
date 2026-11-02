import { describe, expect, it } from "vitest";
import { errorFromResponse } from "@/lib/apiClient";
import { toUserError } from "@/lib/serviceErrors";
import { PLAN_ERROR_CODES, ServiceError } from "@/types/domain";

// P3-05: the compute API answers plan limits with 429 and budgets with 402,
// each with a machine-readable code in the error envelope.
const CASES: Array<[number, string]> = [
  [429, "PLAN_RUNS_PER_MONTH_EXCEEDED"],
  [429, "PLAN_CONCURRENT_JOBS_EXCEEDED"],
  [402, "PLAN_GPU_REQUIRED"],
  [402, "PLAN_TIMELINE_BYTES_EXCEEDED"],
  [402, "BUDGET_EXCEEDED"],
];

describe("plan-limit and budget errors", () => {
  it.each(CASES)("keeps the %i %s code from the envelope", (status, code) => {
    const body = JSON.stringify({ detail: { code, message: "limit 25, used 25" } });
    const err = errorFromResponse(status, body);
    expect(err).toBeInstanceOf(ServiceError);
    expect(err.code).toBe(code);
    expect(err.message).toBe("limit 25, used 25");
  });

  it.each(CASES)("shows a specific message for %i %s", (_status, code) => {
    const ue = toUserError(new ServiceError(code as never, "limit 25, used 25"), "submit-run");
    expect(ue.code).toBe(code);
    expect(ue.title).toBe("Couldn't start the run");
    expect(ue.description).toContain("limit 25, used 25");
    expect(ue.description).not.toMatch(/something went wrong/i);
  });

  it("covers every code the API defines", () => {
    expect([...PLAN_ERROR_CODES].sort()).toEqual(CASES.map(([, c]) => c).sort());
  });

  it("falls back to the status mapping for other envelopes and non-JSON bodies", () => {
    expect(errorFromResponse(404, JSON.stringify({ detail: { code: "NOT_FOUND" } })).code).toBe(
      "NOT_FOUND",
    );
    expect(errorFromResponse(500, "oops").code).toBe("SERVER_ERROR");
    expect(errorFromResponse(500, "oops").message).toBe("oops");
  });
});
