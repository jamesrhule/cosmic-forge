/**
 * Provider-agnostic telemetry shim.
 *
 * No-ops by default. Wire `track`/`pageview` to PostHog, Plausible, or a
 * custom endpoint by replacing the `dispatch` body — every call site
 * keeps its tagged event name and payload.
 *
 * Events fired today:
 *   - "page_view"            — every route mount (root layout effect)
 *   - "run_started"          — ActionsRail.onRun success
 *   - "visualization_opened" — visualizer.$runId.lazy mount
 */

export interface TelemetryEvent {
  name: string;
  props?: Record<string, unknown>;
}

const DEBUG = import.meta.env.DEV;

function dispatch(event: TelemetryEvent): void {
  if (DEBUG) {
    // eslint-disable-next-line no-console
    console.debug("[telemetry]", event.name, event.props ?? {});
  }
  // Hook a real provider here, e.g.:
  //   window.plausible?.(event.name, { props: event.props });
}

export function track(name: string, props?: Record<string, unknown>): void {
  dispatch({ name, props });
}

export function pageview(path: string): void {
  dispatch({ name: "page_view", props: { path } });
}
