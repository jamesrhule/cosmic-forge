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
import { ErrorPage } from "@/components/error-page";
import { Button } from "@/components/ui/button";
import { installChunkErrorListener, pageview, PLAUSIBLE } from "@/lib/telemetry";
import { AuthProvider } from "@/lib/auth";

function NotFoundComponent() {
  return (
    <ErrorPage
      eyebrow="404"
      title="Page not found"
      description="The page you're looking for doesn't exist or has been moved."
      primaryAction={
        <Button asChild>
          <Link to="/">Go home</Link>
        </Button>
      }
    />
  );
}

export const Route = createRootRoute({
  head: () => {
    const meta = [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { name: "theme-color", content: "#0b0b14" },
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
    ];

    const links = [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", type: "image/x-icon", href: "/favicon.ico" },
      { rel: "icon", type: "image/png", sizes: "32x32", href: "/favicon-32.png" },
      { rel: "icon", type: "image/png", sizes: "16x16", href: "/favicon-16.png" },
      { rel: "apple-touch-icon", sizes: "180x180", href: "/apple-touch-icon.png" },
      { rel: "manifest", href: "/manifest.webmanifest" },
    ];

    const scripts = PLAUSIBLE
      ? [
          {
            src: "https://plausible.io/js/script.js",
            "data-domain": PLAUSIBLE,
            defer: true,
          },
        ]
      : [];

    return { meta, links, scripts };
  },
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
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
    return installChunkErrorListener();
  }, []);
  useEffect(() => {
    pageview(pathname);
  }, [pathname]);
  return (
    <AuthProvider>
      <RootErrorBoundary>
        <Outlet />
        <ChatDrawer />
        <ChatTrigger />
        <Toaster richColors closeButton position="bottom-right" />
      </RootErrorBoundary>
    </AuthProvider>
  );
}
