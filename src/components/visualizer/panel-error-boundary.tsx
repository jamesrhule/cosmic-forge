import { Component, type ErrorInfo, type ReactNode } from "react";
import { DataErrorPanel } from "@/components/data-error-panel";
import { notifyServiceError } from "@/lib/serviceErrors";

interface PanelErrorBoundaryProps {
  /** Human label used in the headline. */
  label: string;
  /** Compact layout for split-screen panes. */
  dense?: boolean;
  children: ReactNode;
}

interface PanelErrorBoundaryState {
  /** When set, the panel body has crashed and is rendering DataErrorPanel. */
  error: Error | null;
  /** Bumped on Retry to force the children subtree to remount. */
  resetKey: number;
}

/**
 * Per-panel error boundary.
 *
 * Each visualizer tile renders its own data fast-path; a corrupted frame
 * (mismatched bake buffers, missing `lepton_flow`, etc.) would otherwise
 * unmount the whole workbench through React's default error propagation.
 *
 * On capture we:
 *   1. Render a dense `DataErrorPanel` with a Retry button that remounts
 *      the children so transient render errors recover without a full
 *      route invalidate.
 *   2. Fire a `silent: true` telemetry/notify call. The route loader's
 *      toast already covers genuine load failures; this one is here to
 *      keep the analytics pipeline whole when a render path crashes.
 */
export class PanelErrorBoundary extends Component<
  PanelErrorBoundaryProps,
  PanelErrorBoundaryState
> {
  state: PanelErrorBoundaryState = { error: null, resetKey: 0 };

  static getDerivedStateFromError(error: Error): Partial<PanelErrorBoundaryState> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    notifyServiceError(error, "visualization", {
      silent: true,
      extra: {
        panel: this.props.label,
        componentStack: info.componentStack ?? null,
      },
    });
  }

  private handleRetry = () => {
    this.setState((prev) => ({ error: null, resetKey: prev.resetKey + 1 }));
  };

  render(): ReactNode {
    if (this.state.error) {
      return (
        <DataErrorPanel
          dense={this.props.dense}
          title={`Couldn't render ${this.props.label}`}
          description={
            this.state.error.message ||
            "This panel hit an unexpected error while rendering the current frame."
          }
          onRetry={this.handleRetry}
        />
      );
    }
    // `key` forces a remount on Retry so any cached useMemo / refs reset.
    return <div key={this.state.resetKey} className="h-full w-full">{this.props.children}</div>;
  }
}
