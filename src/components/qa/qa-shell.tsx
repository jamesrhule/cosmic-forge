import { useEffect, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ClientOnly } from "@/components/client-only";
import { enableDevOverlay, disableDevOverlay, isDevOverlayEnabled } from "@/config/dev-overlay";
import { QaConfiguratorFrame } from "./qa-configurator-frame";
import { QaControlFrame } from "./qa-control-frame";
import { QaResearchFrame } from "./qa-research-frame";
import { QaChecklist } from "./qa-checklist";
import type { RunResult, ScanResult } from "@/types/domain";

export type QaTab = "configurator" | "control" | "research" | "checklist";

export interface QaShellProps {
  tab: QaTab;
  runs: RunResult[];
  scan: ScanResult;
}

export function QaShell({ tab, runs, scan }: QaShellProps) {
  const navigate = useNavigate({ from: "/qa" });
  const [overlayOn, setOverlayOn] = useState(false);
  const [badgeCount, setBadgeCount] = useState(0);

  // Auto-enable the dev overlay when /qa mounts so badges appear without
  // any tester action. They can opt out with the header button.
  useEffect(() => {
    enableDevOverlay();
    setOverlayOn(true);
  }, []);

  // Live count of mounted chart-size badges. Drives the header pill so
  // a missing chart is immediately obvious.
  useEffect(() => {
    if (typeof document === "undefined") return;
    const update = () => {
      setBadgeCount(document.querySelectorAll('[data-testid="chart-size-badge"]').length);
    };
    update();
    const obs = new MutationObserver(update);
    obs.observe(document.body, { childList: true, subtree: true });
    const id = window.setInterval(update, 500);
    return () => {
      obs.disconnect();
      window.clearInterval(id);
    };
  }, [tab]);

  const setTab = (next: QaTab) => {
    void navigate({ search: (prev: { tab?: QaTab }) => ({ ...prev, tab: next }) });
  };

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-background/80 px-6 backdrop-blur">
        <Link to="/" className="font-semibold tracking-tight hover:underline">
          UCGLE-F1 Workbench
        </Link>
        <span className="rounded-full border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
          /qa · resize harness
        </span>
        <nav className="ml-6 hidden items-center gap-1 md:flex">
          <Link
            to="/"
            activeOptions={{ exact: true }}
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            activeProps={{
              className: "rounded-md px-3 py-1.5 text-sm bg-accent text-accent-foreground",
            }}
          >
            Configurator
          </Link>
          <Link
            to="/visualizer"
            activeOptions={{ exact: true }}
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            activeProps={{
              className: "rounded-md px-3 py-1.5 text-sm bg-accent text-accent-foreground",
            }}
          >
            Visualizer
          </Link>
          <Link
            to="/qa"
            activeOptions={{ exact: true }}
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            activeProps={{
              className: "rounded-md px-3 py-1.5 text-sm bg-accent text-accent-foreground",
            }}
          >
            QA
          </Link>
        </nav>
        <div className="ml-auto flex items-center gap-2 text-xs">
          <span
            className="rounded-full border px-2 py-0.5 font-mono text-[11px]"
            style={{
              background: overlayOn
                ? "color-mix(in oklab, var(--color-accent-indigo) 18%, transparent)"
                : "var(--color-muted)",
              color: overlayOn ? "var(--color-accent-indigo)" : "var(--color-muted-foreground)",
            }}
          >
            overlay: {overlayOn ? "ON" : "OFF"}
          </span>
          <span className="rounded-full border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
            badges: {badgeCount}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (overlayOn) {
                disableDevOverlay();
              } else {
                enableDevOverlay();
              }
              // Force remount so `ChartSizeBadge`'s `useEffect` re-reads the flag.
              window.location.reload();
            }}
          >
            {overlayOn ? "Disable overlay" : "Enable overlay"}
          </Button>
        </div>
      </header>

      <Tabs value={tab} onValueChange={(v) => setTab(v as QaTab)} className="flex flex-1 flex-col">
        <div className="border-b bg-muted/20 px-6 py-2">
          <TabsList>
            <TabsTrigger value="configurator">Configurator</TabsTrigger>
            <TabsTrigger value="control">Control</TabsTrigger>
            <TabsTrigger value="research">Research</TabsTrigger>
            <TabsTrigger value="checklist">Checklist</TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 overflow-hidden">
          <TabsContent value="configurator" className="m-0 h-full">
            <ClientOnly fallback={<FrameLoading />}>
              {tab === "configurator" && <QaConfiguratorFrame />}
            </ClientOnly>
          </TabsContent>
          <TabsContent value="control" className="m-0 h-full">
            <ClientOnly fallback={<FrameLoading />}>
              {tab === "control" && <QaControlFrame runs={runs} />}
            </ClientOnly>
          </TabsContent>
          <TabsContent value="research" className="m-0 h-full">
            <ClientOnly fallback={<FrameLoading />}>
              {tab === "research" && <QaResearchFrame scan={scan} runs={runs} />}
            </ClientOnly>
          </TabsContent>
          <TabsContent value="checklist" className="m-0 h-full overflow-y-auto">
            <QaChecklist />
          </TabsContent>
        </div>
      </Tabs>

      <footer className="border-t px-6 py-3 text-[11px] text-muted-foreground">
        QA harness · charts resize via ResizeObserver · see{" "}
        <code className="font-mono">docs/qa/chart-resizing.md</code>
      </footer>
    </div>
  );
}

function FrameLoading() {
  return (
    <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
      Loading frame…
    </div>
  );
}
