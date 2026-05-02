/**
 * QCompass — Generic per-domain shell.
 *
 * Reads `getDomain(params.domain)`; 404s if missing or flag-off.
 * Renders a tabbed layout matching the cosmology configurator look.
 *
 * @example
 *   <DomainShell domain={params.domain} active="configurator">{content}</DomainShell>
 */
import type { ReactNode } from "react";
import { Link, notFound } from "@tanstack/react-router";
import { getDomain } from "@/lib/domains/registry";
import "@/lib/domains/register-all";
import type { DomainId, DomainPlugin } from "@/lib/domains/types";
import { Badge } from "@/components/ui/badge";

const DOMAIN_TABS = [
  { key: "configurator", label: "Configurator" },
  { key: "runs", label: "Runs" },
  { key: "research", label: "Research" },
  { key: "visualizer", label: "Visualizer" },
] as const;

export type DomainTab = (typeof DOMAIN_TABS)[number]["key"];

export function resolveDomain(domainParam: string): DomainPlugin<unknown, unknown> {
  const plugin = getDomain(domainParam as DomainId);
  if (!plugin || !plugin.enabled) throw notFound();
  return plugin;
}

export function DomainShell({
  domain,
  active,
  children,
}: {
  domain: DomainPlugin<unknown, unknown>;
  active: DomainTab;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">{domain.label}</h1>
          <p className="text-sm text-muted-foreground">{domain.description}</p>
        </div>
        <div className="flex gap-1">
          {domain.capability.classical && <Badge variant="outline">classical</Badge>}
          {domain.capability.quantum && <Badge variant="outline">quantum</Badge>}
          {domain.capability.audited && <Badge variant="outline">audited</Badge>}
        </div>
      </header>

      <nav className="flex gap-1 border-b" aria-label={`${domain.label} sections`}>
        {DOMAIN_TABS.map((t) => (
          <Link
            key={t.key}
            to={`/domains/$domain/${t.key}` as "/domains/$domain/configurator"}
            params={{ domain: domain.id }}
            className={`border-b-2 px-3 py-2 text-sm transition-colors ${
              active === t.key
                ? "border-primary font-medium text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </Link>
        ))}
      </nav>

      <main>{children}</main>
    </div>
  );
}
