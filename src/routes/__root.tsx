import { useEffect } from "react";
import {
  Outlet,
  Link,
  createRootRoute,
  HeadContent,
  Scripts,
  useRouterState,
} from "@tanstack/react-router";

import appCss from "../styles.css?url";
import { persistDevOverlayFromUrl } from "@/config/dev-overlay";
import { Toaster } from "@/components/ui/sonner";
import { ChatDrawer } from "@/components/chat/chat-drawer";
import { ChatTrigger } from "@/components/chat/chat-trigger";
import { RootErrorBoundary } from "@/components/root-error-boundary";
import { pageview } from "@/lib/telemetry";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">
          Page not found
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6 flex items-center justify-center gap-2">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
          <Link
            to="/visualizer"
            className="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            Open Visualizer
          </Link>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "UCGLE-F1 Workbench" },
      {
        name: "description",
        content:
          "Configure, run, and replay gravitational-leptogenesis simulations with a six-panel visualizer and S1–S15 audit reports.",
      },
      { name: "author", content: "UCGLE Collaboration" },
      { property: "og:title", content: "UCGLE-F1 Workbench" },
      {
        property: "og:description",
        content:
          "Configure, run, and replay gravitational-leptogenesis simulations.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  useEffect(() => {
    persistDevOverlayFromUrl();
  }, []);
  useEffect(() => {
    pageview(pathname);
  }, [pathname]);
  return (
    <RootErrorBoundary>
      <Outlet />
      <ChatDrawer />
      <ChatTrigger />
      <Toaster richColors closeButton position="bottom-right" />
    </RootErrorBoundary>
  );
}
