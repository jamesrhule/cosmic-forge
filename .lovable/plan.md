## Goal

Add a partner-run picker inside the `/visualizer/$runId` header so users can pick (or clear) a B-side run for A↔B comparison without editing the URL by hand. Selection updates the `runB` search param, which already drives the loader and the comparison-mode flow.

## What the user sees

Inside the workbench, next to the existing `← runs` / `runId ↔ runB` breadcrumb in `toolbarLead`, a new compact picker:

```text
[ ← runs ]  kawai-kim-natural  ↔  [ Compare with… ▾ ]
                                   └── starobinsky-standard
                                       gb-off-control
                                       f2-nieh-yan-demo
                                       …
                                       ─────────────
                                       Clear partner
```

- Trigger: small outline button, font-mono `[11px]`, matching the existing breadcrumb chips.
- Label: `Compare with…` when no partner is set, otherwise the partner runId with an `×` affordance.
- Content: searchable list of all run ids that ship a visualization fixture, **excluding** the current `runId` (you can't compare a run to itself).
- Selecting a run → updates `?runB=…`. Selecting **Clear partner** → removes `runB` and forces `mode=single`.
- Disabled with a tooltip hint when only one fixture exists.

## Implementation

### New component: `src/components/visualizer/run-picker.tsx`

- Props: `{ currentRunId: string; partnerRunId: string | null; availableRunIds: string[]; onChange: (runB: string | null) => void; }`
- Uses `Popover` + a Radix `Command` palette (both already installed under `src/components/ui/`) for the searchable list.
- Pure presentational — no router/store imports, so it stays trivially testable.
- Trigger uses the existing breadcrumb chip styling (`rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-muted`).
- Footer row: `Clear partner` (disabled when `partnerRunId` is null).

### Wire into the lazy route: `src/routes/visualizer.$runId.lazy.tsx`

- Read available run ids via the parent route loader: `getRouteApi("/visualizer").useLoaderData().runIds`.
- Replace the hand-rolled `toolbarLead` block with:
  - The existing `← runs` link and the `runId` label.
  - The new `<RunPicker />`, given `currentRunId = params.runId`, `partnerRunId = b?.runId ?? null`, and the filtered `availableRunIds`.
- `onChange` handler navigates with `useNavigate({ from: "/visualizer/$runId" })`:
  - When picking a run: `search: (prev) => ({ ...prev, runB: pickedId })` (preserves `mode`, `phase`, `frame`).
  - When clearing: `search: (prev) => ({ ...prev, runB: undefined, mode: "single" })`.
  - Use `replace: true` to avoid bloating the back stack.
- The route loader's `loaderDeps` already keys on `search.runB`, so the partner timeline is fetched automatically. The existing `useEffect` that mirrors `mode` to the store keeps the comparison state in sync.

### Index page polish (very small)

- `src/routes/visualizer.index.tsx`: update the helper line under the heading from "Add a partner run via the `?runB=` query param or from inside the workbench" to "Add a partner run from the **Compare with…** picker in the workbench header." Keeps the docs honest.

## Out of scope

- No changes to the store, the loader, or the panel components.
- No new fixtures, no new search params.
- No swap-A/B button (can be a follow-up; the picker only writes B).

## Files touched

- **new** `src/components/visualizer/run-picker.tsx`
- **edit** `src/routes/visualizer.$runId.lazy.tsx` (toolbarLead block only)
- **edit** `src/routes/visualizer.index.tsx` (one line of copy)
