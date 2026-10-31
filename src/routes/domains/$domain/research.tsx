import { createFileRoute } from "@tanstack/react-router";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { ParticleSuite } from "@/components/research/particle-suite";

export const Route = createFileRoute("/domains/$domain/research")({
  // Return only serialisable data: the plugin object (components, schemas)
  // can't cross the SSR dehydration boundary (P0-05).
  loader: ({ params }) => {
    const plugin = resolveDomain(params.domain);
    return { domainId: plugin.id, label: plugin.label };
  },
  component: ResearchPage,
  head: ({ loaderData }) => ({
    meta: [{ title: `${loaderData?.label} · Research — QCompass` }],
  }),
});

function ResearchPage() {
  const domain = resolveDomain(Route.useLoaderData().domainId);
  const showParticleSuite =
    domain.id === "hep.lattice" || domain.id === "nuclear.structure";
  return (
    <DomainShell domain={domain} active="research">
      {showParticleSuite ? (
        <ParticleSuite />
      ) : (
        <p className="text-sm text-muted-foreground">
          Domain-specific research surfaces land in the depth pass.
        </p>
      )}
    </DomainShell>
  );
}
