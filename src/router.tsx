// First: zod's CSP setting must precede every schema (src/lib/zod-csp.ts).
import "@/lib/zod-csp";
import { createRouter, Link, useRouter, type ErrorComponentProps } from "@tanstack/react-router";
import { QueryClient } from "@tanstack/react-query";
import { routeTree } from "./routeTree.gen";
import { ErrorPage } from "@/components/error-page";
import { Button } from "@/components/ui/button";
import { getCspNonce } from "@/lib/csp-nonce";

function DefaultErrorComponent({ error, reset }: ErrorComponentProps) {
  const router = useRouter();

  return (
    <ErrorPage
      eyebrow="Error"
      title="Something went wrong"
      description="An unexpected error occurred. Try again, or open the assistant for help."
      errorMessage={error instanceof Error ? error.message : String(error)}
      primaryAction={
        <>
          <Button
            onClick={() => {
              router.invalidate();
              reset();
            }}
          >
            Try again
          </Button>
          <Button asChild variant="outline">
            <Link to="/">Go home</Link>
          </Button>
        </>
      }
    />
  );
}

export const getRouter = () => {
  // Fresh QueryClient per router instance — never a module-level
  // singleton, otherwise SSR caches leak between requests.
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
    defaultErrorComponent: DefaultErrorComponent,
    // CSP nonce for the inline scripts Start streams (src/lib/csp.ts).
    ssr: { nonce: getCspNonce() },
  });

  return router;
};
