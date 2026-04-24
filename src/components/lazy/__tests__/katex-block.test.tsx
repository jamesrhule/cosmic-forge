import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import LazyBlockMath from "@/components/lazy/katex-block";

describe("LazyBlockMath", () => {
  it("renders simple LaTeX into a KaTeX HTML tree", () => {
    const { container } = render(<LazyBlockMath math="E = mc^2" />);
    const root = container.querySelector('[data-testid="react-katex"]');
    expect(root).not.toBeNull();
    // KaTeX always emits a top-level .katex wrapper around the rendered tree.
    expect(root?.querySelector(".katex")).not.toBeNull();
    // Fallback path must NOT be triggered for valid input.
    expect(container.querySelector("[data-katex-fallback]")).toBeNull();
  });

  it("preserves \\htmlId targets used by the formula-glow contract", () => {
    const { container } = render(
      <LazyBlockMath math="\htmlId{vfx-xi}{\xi} + \htmlId{vfx-M1}{M_1}" />,
    );
    expect(container.querySelector("#vfx-xi")).not.toBeNull();
    expect(container.querySelector("#vfx-M1")).not.toBeNull();
  });

  it("falls back to raw LaTeX for pathological input — never throws", () => {
    // `\fakecommand{` is unknown AND has an unbalanced brace — KaTeX
    // either emits a katex-error span or, in some builds, throws.
    // Either way our component must keep the screen alive.
    const { container } = render(<LazyBlockMath math="\fakecommand{" />);
    const fallback = container.querySelector("[data-katex-fallback]");
    const errorSpan = container.querySelector(".katex-error");
    // Exactly one of the two safe outputs must be present.
    expect(Boolean(fallback) || Boolean(errorSpan)).toBe(true);
  });
});
