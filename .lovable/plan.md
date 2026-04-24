# Build review — fixes

I reviewed the running shell. Build compiles cleanly; the dev-server `tailwind.config.ts` warning is benign (project is on Tailwind v4 with CSS-based config — no action). Two real issues plus a couple of small tidies:

## Issues found

### 1. F1 equation crashes KaTeX with "Double superscript" (real bug, visible to user)

Captured from the session replay:

> KaTeX parse error: Double superscript at position 323: …0\times 10^{18}^2}_{M_\star^{...

Cause: `src/lib/equationFormatter.ts` builds the M⋆² term as `${sciTex(c.M_star)}^2`. With `M_star = 2.4e18`, `sciTex` returns `2.40\times 10^{18}` — already ending in a superscript — so appending `^2` produces an invalid `10^{18}^2`. Whenever the user picks any value where the mantissa is not 1 (i.e. almost always), the equation block renders red KaTeX error text instead of the boxed F1.

**Fix:** wrap the scientific-notation literal in braces before squaring, and use a dedicated helper so the intent is explicit. New helper `sciTexPow(v, exp)` returns `\left(<sciTex>\right)^{<exp>}`. Replace the offending line with `\\underbrace{${sciTexPow(c.M_star, 2)}}_{M_\\star^{\\,2}}`.

### 2. Recharts logs `width(0) and height(0)` warnings on narrow viewports

Cause: `NarrowScreenGate` always renders both branches in the DOM — the wide branch uses `hidden lg:block`, so at the user's current 677px viewport the `<PotentialPreviewChart>` (and any other ResponsiveContainer) is mounted inside a `display: none` subtree. ResponsiveContainer measures 0×0 and warns repeatedly. Cosmetic, but spammy and worth fixing.

**Fix:** make `NarrowScreenGate` *conditional*, not CSS-only. Use a small `useMediaQuery("(min-width: 1024px)")` hook (built on `window.matchMedia`, mounted via `useIsMounted` to stay SSR-safe) and render either the wide layout *or* the narrow card, never both. Default to the narrow card during SSR so server output doesn't pre-render charts that the client may immediately unmount.

### 3. Minor tidy

- `src/routes/index.tsx` ends with `void Button;` — leftover lint silencer that's no longer needed (Button is used inside `Configurator`/cards but not directly in the route file). Drop the import and the `void` line cleanly.
- `useEffect(() => void form.trigger(), [])` with eslint-disable. Replace with `useForm({ ..., mode: "onChange", reValidateMode: "onChange", criteriaMode: "all" })` plus a one-shot `trigger` inside an effect that lists `form` as a dep — keeps validation fresh without the lint suppression.

## Files touched

- **edit `src/lib/equationFormatter.ts`** — add `sciTexPow`, swap the M⋆² line to use it, leave every other token unchanged.
- **new `src/hooks/use-media-query.ts`** — tiny SSR-safe `matchMedia` hook returning a boolean.
- **edit `src/routes/index.tsx`** — `NarrowScreenGate` becomes a conditional render using the new hook; remove the trailing `void Button;` and the unused `Button` import; tighten the validation effect.

## Out of scope

Tailwind config esbuild warning (project intentionally has no `tailwind.config.ts` — it's a Tailwind v4 CSS-config setup, the warning comes from a tooling generator and does not affect dev/build). No code change here.
