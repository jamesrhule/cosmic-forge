# Accessibility Checklist

Single-page reference for production accessibility checks. Walk this list
before every release. Items are grouped by surface; each box should be
verifiable in under a minute.

## Global

- [ ] Every interactive element receives a visible focus ring
      (`focus-visible:ring-2 focus-visible:ring-ring`). Custom sliders,
      chips, panels, and icon buttons included.
- [ ] Tab order through `<ResizablePanelGroup>` follows visual order:
      left form column → handle → centre previews → handle → right rail.
      Arrow keys resize when the handle is focused.
- [ ] No element has `tabindex` greater than 0.
- [ ] All `<img>` and `<svg>` decorative icons have either an `alt=""`
      or `aria-hidden="true"`. Informational icons have `aria-label`.
- [ ] Colour contrast: body text ≥ 4.5:1, large text ≥ 3:1. Verify on
      both `light` and `dark` themes (we bumped `--muted-foreground` for
      dark mode — confirm with the WebAIM contrast checker).
- [ ] Honour `prefers-reduced-motion`: PhaseSpace `useFrame` loop,
      transport autoplay, and panel-skeleton pulses pause when the
      media query matches.
- [ ] Initial theme is seeded from `prefers-color-scheme` when no
      persisted value exists.

## Chat drawer

- [ ] Drawer opens/closes via keyboard (Enter on trigger, Esc to close).
- [ ] Composer textarea is the first focused element when the drawer
      opens; focus returns to the trigger on close.
- [ ] Streaming token output sits inside an `aria-live="polite"` region
      so screen readers announce updates without stealing focus.
- [ ] Send button is disabled while streaming and re-enabled when the
      stream finishes or is aborted.
- [ ] Closing the drawer mid-stream aborts the request (no orphaned
      generators).
- [ ] Context chip strip is keyboard-removable (Tab to chip, Enter on
      the X button).

## Visualizer

- [ ] Each panel header has an `aria-label` describing the metric.
- [ ] Transport controls (Play/Pause/Step) expose `aria-label` and
      `aria-pressed` (for the Play toggle).
- [ ] Frame slider behaves as a native range input — Arrow keys step
      one frame, PgUp/PgDn step ten, Home/End jump to bounds.
- [ ] Run-progress indicator is wrapped in `aria-live="polite"`.
- [ ] PhaseSpace canvas has a sibling text summary (frame index, τ,
      ψ, ψ′) for non-visual users.
- [ ] Empty-state and error cards include an "Open assistant" action.

## Configurator

- [ ] Every form control has an associated `<Label>` (no orphaned
      placeholders).
- [ ] Validity light is announced via `aria-live="polite"` and pairs
      with text (`status: warning`, not just colour).
- [ ] Cost badge uses both colour and text.
- [ ] Submit button reflects validity in `aria-disabled` (not just
      `disabled`) so screen readers describe why it's unavailable.

## Errors and 404

- [ ] `RootErrorBoundary`, route-level `errorComponent`, and
      `notFoundComponent` all render the shared `<ErrorPage>` shell with
      the brand mark, primary action, and an "Open assistant" affordance.
- [ ] `<title>` is updated for error states so the browser tab is
      meaningful.

## Service / loading states

- [ ] `getRun`, `getBenchmarks`, `getVisualization`, and every
      `loadFixture` consumer surfaces a `toast.error` on failure (in
      addition to the route's `errorComponent`).
- [ ] Offline mode (DevTools → Network → Offline) shows readable text,
      not blank panels.
- [ ] `chunk_load_error` telemetry fires when a lazy chunk fails (deploy
      mismatch, network drop).
