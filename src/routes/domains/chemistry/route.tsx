import { createFileRoute, Outlet, Link } from "@tanstack/react-router";
import { FEATURES } from "@/config/features";
import { DomainSwitcher } from "@/components/qcompass/domain-switcher";
import { cn } from "@/lib/utils";

/**
 * Chemistry-domain layout. Wraps every `/domains/chemistry/*` page
 * with the same top-nav (mode pill + DomainSwitcher) so cosmology
 * views remain untouched.
 *
 * The route is gated by `FEATURES.qcompassMultiDomain`. When the
 * flag is false the layout renders a small "feature off" notice
 * with a link back to the cosmology workbench, so deep-linking to
 * `/domains/chemistry/configurator` never breaks the app.
 */
export const Route = createFileRoute("/domains/chemistry")({
  component: ChemistryLayout,
});

function ChemistryLayout() {
  if (!FEATURES.qcompassMultiDomain) {
    return <DisabledNotice />;
  }
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background/80 px-6 backdrop-blur">
        <span className="font-semibold tracking-tight">QCompass · Chemistry</span>
        <span className="rounded-full border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
          fixture mode
        </span>
        <div className="ml-4">
          <DomainSwitcher />
        </div>
        <nav className="ml-auto flex items-center gap-1 text-xs">
          <TabLink to="/domains/chemistry/configurator" label="Configurator" />
          <TabLink to="/domains/chemistry/runs" label="Runs" />
          <TabLink to="/domains/chemistry/research" label="Research" />
        </nav>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}

interface TabLinkProps {
  to: string;
  label: string;
}

function TabLink({ to, label }: TabLinkProps) {
  return (
    <Link
      to={to}
      activeOptions={{ exact: false }}
      className={cn(
        "rounded-md px-2.5 py-1 text-muted-foreground transition-colors hover:text-foreground",
      )}
      activeProps={{
        className: "bg-muted text-foreground font-medium",
      }}
    >
      {label}
    </Link>
  );
}

function DisabledNotice() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="max-w-md space-y-3 text-center">
        <h1 className="text-xl font-semibold">Chemistry domain is disabled</h1>
        <p className="text-sm text-muted-foreground">
          Set <code className="font-mono">FEATURES.qcompassMultiDomain = true</code>{" "}
          in <code className="font-mono">src/config/features.ts</code> to expose
          the chemistry workbench. The cosmology shell at{" "}
          <Link to="/" className="text-[color:var(--accent-indigo)] underline">
            /
          </Link>{" "}
          is unaffected by this flag.
        </p>
      </div>
    </div>
  );
}
