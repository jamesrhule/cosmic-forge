import { Link, useLocation } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

/**
 * Top-nav domain switcher.
 *
 * Visible when `FEATURES.qcompassMultiDomain === true`. The active
 * domain is inferred from the current pathname:
 *   /                         → cosmology
 *   /domains/chemistry/...    → chemistry
 *
 * Placement: rendered next to the header's mode pill. Cosmology is
 * always reachable via "/" so the existing index route is preserved.
 */
export function DomainSwitcher() {
  const { pathname } = useLocation();
  const isChemistry = pathname.startsWith("/domains/chemistry");
  const isCosmology = !isChemistry;

  return (
    <nav
      aria-label="Research domain"
      className="flex items-center gap-1 rounded-full border bg-muted/40 p-0.5 text-[11px]"
    >
      <DomainPill
        to="/"
        label="Cosmology · UCGLE-F1"
        active={isCosmology}
      />
      <DomainPill
        to="/domains/chemistry/configurator"
        label="Chemistry"
        active={isChemistry}
      />
      <DomainPill label="Condensed matter" disabled />
      <DomainPill label="High-energy" disabled />
    </nav>
  );
}

interface DomainPillProps {
  label: string;
  to?: string;
  active?: boolean;
  disabled?: boolean;
}

function DomainPill({ label, to, active, disabled }: DomainPillProps) {
  const base =
    "flex items-center rounded-full px-2.5 py-1 transition-colors";
  if (disabled || !to) {
    return (
      <span
        aria-disabled="true"
        title="Future domain (disabled)"
        className={cn(
          base,
          "cursor-not-allowed text-muted-foreground/60",
        )}
      >
        {label}
      </span>
    );
  }
  return (
    <Link
      to={to}
      className={cn(
        base,
        active
          ? "bg-[color:var(--accent-indigo)] text-[color:var(--accent-indigo-foreground)] font-medium"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </Link>
  );
}
