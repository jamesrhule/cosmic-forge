import { describe, expect, it } from "vitest";
import { redactArgs } from "@/lib/audit";

describe("redactArgs", () => {
  it("redacts known-sensitive keys regardless of casing", () => {
    // SENSITIVE_KEYS lowercases the field name before matching, so any
    // case variant of `password`, `token`, `api_key`, `authorization`,
    // `auth`, or `approval_token` is redacted. Note: `apiKey` lowercases
    // to `apikey` which is *not* in the set — only the snake_case
    // `api_key` form matches. That's intentional; the audit logger
    // canonicalises tool args to snake_case before redaction.
    const out = redactArgs({
      password: "hunter2",
      Token: "abc",
      API_KEY: "k",
      Authorization: "Bearer x",
      keep: "ok",
    }) as Record<string, unknown>;
    expect(out.password).toBe("[redacted]");
    expect(out.Token).toBe("[redacted]");
    expect(out.API_KEY).toBe("[redacted]");
    expect(out.Authorization).toBe("[redacted]");
    expect(out.keep).toBe("ok");
  });

  it("recurses into nested objects and arrays", () => {
    const out = redactArgs({
      nested: { secret: "s", deeper: { token: "t", note: "kept" } },
      list: [{ password: "p" }, "raw"],
    }) as { nested: { secret: string; deeper: { token: string; note: string } }; list: unknown[] };
    expect(out.nested.secret).toBe("[redacted]");
    expect(out.nested.deeper.token).toBe("[redacted]");
    expect(out.nested.deeper.note).toBe("kept");
    expect((out.list[0] as { password: string }).password).toBe("[redacted]");
    expect(out.list[1]).toBe("raw");
  });

  it("truncates very long strings with a marker", () => {
    const long = "x".repeat(2500);
    const out = redactArgs(long) as string;
    expect(out.length).toBeLessThan(long.length);
    expect(out).toContain("…[truncated");
  });

  it("passes through primitives unchanged", () => {
    expect(redactArgs(null)).toBeNull();
    expect(redactArgs(undefined)).toBeUndefined();
    expect(redactArgs(42)).toBe(42);
    expect(redactArgs(true)).toBe(true);
    expect(redactArgs("short")).toBe("short");
  });
});
