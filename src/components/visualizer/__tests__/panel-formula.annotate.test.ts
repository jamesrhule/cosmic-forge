import { describe, expect, it } from "vitest";
import { annotateLatex } from "@/lib/annotateLatex";

describe("annotateLatex", () => {
  it("wraps known term IDs with \\htmlId{vfx-<id>}", () => {
    const out = annotateLatex("\\xi + M_1", ["xi", "M1"]);
    expect(out).toContain("\\htmlId{vfx-xi}{\\xi}");
    expect(out).toContain("\\htmlId{vfx-M1}{M_1}");
  });

  it("substitutes longer fragments before shorter ones (Mstar before M1)", () => {
    // If `M1` were substituted first, the leading `M_` of `M_\star^2`
    // would be consumed and `Mstar` would silently no-op.
    const out = annotateLatex("M_\\star^2 \\cdot M_1", ["M1", "Mstar"]);
    expect(out).toContain("\\htmlId{vfx-Mstar}{M_\\star^2}");
    expect(out).toContain("\\htmlId{vfx-M1}{M_1}");
  });

  it("silently skips unknown term IDs", () => {
    const before = "E = mc^2";
    const out = annotateLatex(before, ["definitely_not_a_term"]);
    expect(out).toBe(before);
  });

  it("only wraps the first occurrence of a fragment", () => {
    // Pinning the current contract: if we ever switch to global wrap
    // this test should be updated intentionally (duplicate DOM IDs would
    // break the formula-glow `[id^='vfx-']` selector).
    const out = annotateLatex("\\xi + \\xi", ["xi"]);
    const matches = out.match(/\\htmlId\{vfx-xi\}/g) ?? [];
    expect(matches).toHaveLength(1);
  });
});
