import { describe, expect, it } from "vitest";
import { z } from "zod";
import { toUserError } from "@/lib/serviceErrors";
import { ServiceError } from "@/types/domain";

describe("toUserError", () => {
  it("maps NOT_FOUND to a fixture-missing description", () => {
    const ue = toUserError(new ServiceError("NOT_FOUND", "missing"), "visualization");
    expect(ue.code).toBe("NOT_FOUND");
    expect(ue.title).toMatch(/visualization/i);
    expect(ue.description).toMatch(/missing/i);
  });

  it("maps INVALID_INPUT to FIXTURE_INVALID", () => {
    const ue = toUserError(new ServiceError("INVALID_INPUT", "bad shape"), "benchmarks");
    expect(ue.code).toBe("FIXTURE_INVALID");
    expect(ue.description).toContain("bad shape");
  });

  it("maps UPSTREAM_FAILURE to a backend-unreachable description", () => {
    const ue = toUserError(new ServiceError("UPSTREAM_FAILURE", "503"), "runs");
    expect(ue.code).toBe("UPSTREAM_FAILURE");
    expect(ue.description).toMatch(/backend/i);
  });

  it("flags ZodError as FIXTURE_INVALID with the offending path", () => {
    const schema = z.object({ a: z.object({ b: z.number() }) });
    const result = schema.safeParse({ a: { b: "not a number" } });
    if (result.success) throw new Error("expected failure");
    const ue = toUserError(result.error, "visualization");
    expect(ue.code).toBe("FIXTURE_INVALID");
    expect(ue.description).toContain("a.b");
  });

  it("treats AbortError as STREAM_ABORTED", () => {
    const err = new Error("aborted");
    err.name = "AbortError";
    const ue = toUserError(err, "assistant");
    expect(ue.code).toBe("STREAM_ABORTED");
  });

  it("falls back to UNKNOWN for unrecognised throw values", () => {
    expect(toUserError("string thrown", "audit").code).toBe("UNKNOWN");
    expect(toUserError(42, "audit").code).toBe("UNKNOWN");
    expect(toUserError(null, "audit").code).toBe("UNKNOWN");
  });
});
