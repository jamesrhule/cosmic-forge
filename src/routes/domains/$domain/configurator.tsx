import { createFileRoute, useNavigate, useParams } from "@tanstack/react-router";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { QcompassManifestForm } from "@/components/configurator/QcompassManifestForm";
import { startRun } from "@/services/qcompass/runs";
import { toast } from "sonner";

export const Route = createFileRoute("/domains/$domain/configurator")({
  // Return only serialisable data: the plugin object (components, schemas)
  // can't cross the SSR dehydration boundary (P0-05).
  loader: ({ params }) => {
    const plugin = resolveDomain(params.domain);
    return { domainId: plugin.id, label: plugin.label };
  },
  component: ConfiguratorPage,
  head: ({ loaderData }) => ({
    meta: [{ title: `${loaderData?.label} · Configurator — QCompass` }],
  }),
});

function ConfiguratorPage() {
  const domain = resolveDomain(Route.useLoaderData().domainId);
  const { domain: domainId } = useParams({ from: "/domains/$domain/configurator" });
  const navigate = useNavigate();
  return (
    <DomainShell domain={domain} active="configurator">
      <QcompassManifestForm
        domain={domain.id}
        onSubmit={async (data) => {
          const { runId } = await startRun(domain.id, data);
          toast.success(`Queued run ${runId}`, { description: domainId });
          // Land on the run so its result and provenance are visible (P0-06).
          await navigate({
            to: "/domains/$domain/runs/$id",
            params: { domain: domain.id, id: runId },
          });
        }}
      />
    </DomainShell>
  );
}
