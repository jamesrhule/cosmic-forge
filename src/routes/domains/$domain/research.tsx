import { createFileRoute } from "@tanstack/react-router";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { ParticleSuite } from "@/components/research/particle-suite";

export const Route = createFileRoute("/domains/$domain/research")({
  loader: ({ params }) => ({ domain: resolveDomain(params.domain) }),
  component: ResearchPage,
  head: ({ loaderData }) => ({
    meta: [{ title: `${loaderData?.domain.label} · Research — QCompass` }],
  }),
});

function ResearchPage() {
  const { domain } = Route.useLoaderData();
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
