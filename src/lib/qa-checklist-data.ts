/**
 * Structured copy of `docs/qa/chart-resizing.md`.
 *
 * The markdown file remains the source of truth. This module mirrors it
 * for rendering inside the `/qa` dashboard so testers can tick rows off
 * with persistent state. If you edit the markdown, update this file too
 * — code review will surface the diff.
 */

export interface QaChecklistRow {
  /** Stable id used as the localStorage key. Never reuse. */
  id: string;
  step: string;
  expected: string;
}

export interface QaChecklistSection {
  title: string;
  /** Optional intro paragraph rendered above the rows. */
  intro?: string;
  rows: QaChecklistRow[];
}

export const QA_CHECKLIST: QaChecklistSection[] = [
  {
    title: "Setup",
    intro:
      "Open DevTools → Console. The console must stay free of `width(0) and height(0)`, `findDOMNode is deprecated`, and any `ResizeObserver loop` errors.",
    rows: [
      {
        id: "setup.console-clean",
        step: "Hard reload `/qa` and watch the console.",
        expected: "No Recharts/ResizeObserver warnings.",
      },
      {
        id: "setup.overlay-on",
        step: "Confirm the dev-overlay pill in the header reads ON.",
        expected: "Every chart shows a black `label · w×h · n=…` badge in its top-right corner.",
      },
    ],
  },
  {
    title: "Configurator",
    intro: 'Charts under test: V(ψ) preview (`label="vψ"`).',
    rows: [
      {
        id: "cfg.first-paint",
        step: "Switch to the Configurator tab.",
        expected: "vψ paints once at correct size; n starts at 1 or 2.",
      },
      {
        id: "cfg.drag-left",
        step: "Drag the left resizable handle slowly right, then back left.",
        expected: "vψ width updates within one frame; n increments smoothly.",
      },
      {
        id: "cfg.drag-right",
        step: "Drag the right resizable handle.",
        expected: "Middle column shrinks/grows; w tracks.",
      },
      {
        id: "cfg.accordion",
        step: "Collapse the Potential accordion, then re-open it.",
        expected: "Chart remounts at correct size on re-open; no warnings.",
      },
    ],
  },
  {
    title: "Control",
    intro: 'Charts under test: SGWB plot (`label="sgwb"`).',
    rows: [
      {
        id: "ctl.first-paint",
        step: "Switch to the Control tab.",
        expected: "SGWB paints once at correct size; no width(0) warnings.",
      },
      {
        id: "ctl.drag-handle",
        step: "Drag the run-list / detail handle.",
        expected: "SGWB plot tracks live; n increments.",
      },
      {
        id: "ctl.switch-run",
        step: "Switch between two runs in the run list.",
        expected: "Chart remounts at the same size; counter resets.",
      },
      {
        id: "ctl.tab-roundtrip",
        step: "Switch to Configurator and back to Control.",
        expected: "No stale dimensions; chart re-measures on re-mount.",
      },
    ],
  },
  {
    title: "Research",
    intro:
      'Charts under test: ξ×θ ParameterHeatmap (`label="η-scan"`) and side-by-side SGWB tiles.',
    rows: [
      {
        id: "res.first-paint",
        step: "Switch to the Research tab.",
        expected:
          "Heatmap badge shows current container size; both SGWB tiles show distinct widths.",
      },
      {
        id: "res.drag-split",
        step: "Drag the heatmap / tiles split.",
        expected: "Heatmap and tiles re-measure cleanly; no overlap.",
      },
      {
        id: "res.viewport",
        step: "Resize the browser window between ~1024px and full-width.",
        expected: "Every chart still tracks viewport (window-resize path).",
      },
    ],
  },
  {
    title: "Edge cases",
    rows: [
      {
        id: "edge.ssr",
        step: "View page source for `/qa`.",
        expected: "Initial HTML contains no `<svg>` chart markup (client-mounted).",
      },
      {
        id: "edge.cpu-throttle",
        step: "Throttle CPU 4× in DevTools, repeat the drag tests.",
        expected: "Chart still keeps up — one update per frame, not per pointer event.",
      },
    ],
  },
];

export function flatRowIds(): string[] {
  return QA_CHECKLIST.flatMap((s) => s.rows.map((r) => r.id));
}
