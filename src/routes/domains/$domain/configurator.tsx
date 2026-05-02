import { createFileRoute, useParams } from "@tanstack/react-router";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { QcompassManifestForm } from "@/components/configurator/QcompassManifestForm";
import { startRun } from "@/services/qcompass/runs";
import { toast } from "sonner";

export const Route = createFileRoute("/domains/$domain/configurator")({
  loader: ({ params }) => ({ domain: resolveDomain(params.domain) }),
  component: ConfiguratorPage,
  head: ({ loaderData }) => ({
    meta: [{ title: `${loaderData?.domain.label} · Configurator — QCompass` }],
  }),
});

function ConfiguratorPage() {
  const { domain } = Route.useLoaderData();
  const { domain: domainId } = useParams({ from: "/domains/$domain/configurator" });
  return (
    <DomainShell domain={domain} active="configurator">
      <QcompassManifestForm
        domain={domain.id}
        onSubmit={async (data) => {
          const { runId } = await startRun(domain.id, data);
          toast.success(`Queued run ${runId}`, { description: domainId });
        }}
      />
    </DomainShell>
  );
}
