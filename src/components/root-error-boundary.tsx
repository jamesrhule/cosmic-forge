import { Component, type ReactNode } from "react";
import { ErrorPage } from "@/components/error-page";
import { Button } from "@/components/ui/button";

interface State {
  error: Error | null;
}

/**
 * Catches errors thrown inside event handlers, rAF loops, ResizeObserver
 * callbacks, and other places TanStack Router's loader/render boundary
 * doesn't see. Keeps the chrome (header, toaster, chat drawer) usable so
 * the user can navigate away.
 *
 * Renders the shared `ErrorPage` so the recovery UI matches the rest of
 * the chrome (brand mark, primary/secondary actions, "Open assistant").
 */
export class RootErrorBoundary extends Component<
  { children: ReactNode },
  State
> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    // eslint-disable-next-line no-console
    console.error("[RootErrorBoundary]", error);
  }

  render() {
    if (this.state.error) {
      return (
        <ErrorPage
          eyebrow="Error"
          title="Something went wrong"
          description="An unexpected error occurred. Reload the page to recover, or open the assistant for help."
          errorMessage={this.state.error.message}
          primaryAction={
            <Button
              type="button"
              onClick={() => {
                this.setState({ error: null });
                if (typeof window !== "undefined") window.location.reload();
              }}
            >
              Reload
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
