## Goal

Make the live JSONL stream from `streamVisualization` visible while frames arrive. Today the service exists, my last patch added abort + error mapping, but **nothing in the UI actually consumes it** — there's no way for a viewer to see "30 / 60 frames received" or feel that data is flowing. This adds a visible progress indicator (and a small dev affordance to actually exercise it on the bundled fixture).

## Stream metadata

`public/fixtures/visualizations/streams/kawai-kim-live.jsonl` ships 60 frames at a 50ms cadence (~3s end-to-end). The fixture is the same shape as a single `VisualizationFrame`, so frames can replace timeline entries one-by-one once they arrive.

## Changes

### 1. Service tweaks — `src/services/visualizer.ts`
- Add an optional `{ signal?: AbortSignal; delayMs?: number }` arg to `streamVisualization` and forward `signal` into `loadJsonlFixture` (the underlying helper already supports it). This lets the consumer cancel mid-stream when the user toggles Live off or navigates away.
- Add a tiny `getStreamFrameCount(runId)` helper that does a one-shot HEAD-then-GET on the JSONL fixture and returns the line count (or `null` if unknown). Used by the indicator to render a meaningful denominator before the first frame lands.

### 2. New consumer hook — `src/hooks/useVisualizationStream.ts`
A small zero-dep hook returning:
```ts
{
  status: "idle" | "connecting" | "streaming" | "complete" | "error" | "cancelled",
  framesReceived: number,
  framesExpected: number | null,
  lastFrame: VisualizationFrame | null,
  error: Error | null,
  start: () => void,
  stop: () => void,
}
```
Internals:
- Owns a single `AbortController`. `start()` allocates a fresh one and walks the async iterable; `stop()` aborts it.
- Pre-fetches `getStreamFrameCount(runId)` in parallel so the denominator appears immediately.
- Handles `ServiceError`/`AbortError` and routes load failures through the existing `notifyServiceError(err, "visualization")` helper so the toast stays consistent with my prior pass.
- Cleans up on unmount (auto-aborts).

### 3. New component — `src/components/visualizer/streaming-progress-indicator.tsx`
A compact pill (~ same height as the existing comparison toggles) suitable for the visualizer header. Visual layout:
```text
[● Streaming]  ━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░  24 / 60
```
- Status dot color via semantic tokens:
  - `idle`/`cancelled` → `bg-muted-foreground/40`
  - `connecting` → `bg-warning` with the existing `status-pulse` keyframe (already in `styles.css`)
  - `streaming` → `bg-primary` with `status-pulse`
  - `complete` → `bg-success`
  - `error` → `bg-destructive`
- Progress bar uses `<Progress>` from shadcn/ui (`@/components/ui/progress`) — no new primitives. When `framesExpected` is `null`, swap the bar for an indeterminate striped track (`bg-[length:200%_100%]` + `animate-[shimmer_1.4s_linear_infinite]`; add the keyframe to `styles.css`).
- Counter text is mono / tabular-nums to avoid jitter as digits change.
- ARIA: wrap in `role="status"` `aria-live="polite"` so a screen reader hears "24 of 60 frames received".
- Reduced-motion: skips the shimmer animation (uses `usePrefersReducedMotion`).
- Renders nothing when status is `idle` AND no prior session exists — keeps the chrome quiet by default.

### 4. Wire the indicator into the workbench — `src/components/visualizer/visualizer-layout.tsx` and `src/routes/visualizer.$runId.lazy.tsx`
- Add a `LiveStreamControl` in the workbench header next to the Export button. Compact two-element group:
  - `<Toggle>` labelled "Live" (icon: `Radio` from lucide). Pressed = stream is active, unpressed = stop.
  - `<StreamingProgressIndicator>` next to it.
- Pass the master-timeline run id from the lazy route (`a.runId`) into the layout so the hook knows what to stream.
- The hook is only mounted (and the toggle only appears) when the visualizer route has a `timelineA` — the `/visualizer` index doesn't load it.
- When `lastFrame` arrives we **don't** mutate baked buffers; the indicator is purely status-bar UX in this pass. (Live frame splicing onto the panels is a separate, larger change tracked under "live backend cutover".)

### 5. Styles — `src/styles.css`
- Add a `@keyframes shimmer { from { background-position: 200% 0 } to { background-position: -200% 0 } }` and a `.stream-shimmer` utility for the indeterminate state. (Single small additive block; no token changes.)

## Out of scope
- Splicing streamed frames into the live panels (deferred — current panels read baked, immutable timelines; live splicing needs a separate contract).
- Live backend cutover. The toggle only walks the bundled JSONL today; once `FEATURES.liveVisualization` is on, the same hook will transparently consume the WS path.
- Changing the run-list index page.

## Files touched

- `src/services/visualizer.ts` — `streamVisualization` accepts `{ signal, delayMs }`; new `getStreamFrameCount`.
- `src/hooks/useVisualizationStream.ts` — new hook.
- `src/components/visualizer/streaming-progress-indicator.tsx` — new component.
- `src/components/visualizer/visualizer-layout.tsx` — header gets `<LiveStreamControl />`; new optional `runIdA` prop wiring.
- `src/routes/visualizer.$runId.lazy.tsx` — pass `a.runId` into the layout.
- `src/styles.css` — `shimmer` keyframe + `.stream-shimmer` utility.

## Verification

- `bun run typecheck` clean.
- Open `/visualizer/kawai-kim-natural`, click **Live** in the header → progress pill animates from `0 / 60` to `60 / 60` over ~3s and lands on the green "Complete" state.
- Click **Live** again mid-stream → status flips to "Cancelled", abort is honoured (no late `framesReceived` updates after toggle-off).
- Set `prefers-reduced-motion: reduce` → no shimmer, no pulse; counter still updates.
- Corrupt the JSONL fixture → indicator flips to red "Stream failed" and the existing visualization toast fires once via `notifyServiceError`.
