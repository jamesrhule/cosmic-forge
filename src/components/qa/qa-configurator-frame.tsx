import { useDeferredValue, useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EquationBlock } from "@/components/equation-block";
import { ValidityLight } from "@/components/validity-light";
import { CostBadge } from "@/components/cost-badge";
import { PotentialCard } from "@/components/configurator/PotentialCard";
import { CouplingsCard } from "@/components/configurator/CouplingsCard";
import { SeesawCard } from "@/components/configurator/SeesawCard";
import { ReheatingCard } from "@/components/configurator/ReheatingCard";
import { kawaiKimDefaults } from "@/lib/configDefaults";
import { RunConfigSchema } from "@/lib/configSchema";
import { renderF1WithValues } from "@/lib/equationFormatter";
import { checkConfigValidity } from "@/lib/validity";
import type { RunConfig } from "@/types/domain";

/**
 * Standalone copy of the Configurator's 3-panel layout for use inside
 * the `/qa` dashboard. Mirrors `src/routes/index.tsx` so the resize
 * behaviour under test is identical, but without the actions rail
 * (which is stateful and pulls fixtures the QA page doesn't need).
 */
export function QaConfiguratorFrame() {
  const form = useForm<RunConfig>({
    resolver: zodResolver(RunConfigSchema),
    defaultValues: kawaiKimDefaults(),
    mode: "onChange",
  });

  const { control, watch, setValue, formState } = form;
  const config = watch();
  const deferred = useDeferredValue(config);
  const validity = useMemo(() => checkConfigValidity(deferred), [deferred]);
  const f1Latex = useMemo(() => renderF1WithValues(deferred), [deferred]);

  useEffect(() => {
    void form.trigger();
  }, [form]);

  return (
    <ResizablePanelGroup orientation="horizontal" className="h-full">
      <ResizablePanel defaultSize={28} minSize={22} maxSize={40}>
        <div className="h-full overflow-y-auto border-r bg-muted/30 p-4">
          <Accordion
            type="multiple"
            defaultValue={["potential", "couplings", "seesaw", "reheating"]}
            className="space-y-2"
          >
            <Section value="potential" title="Potential V(Ψ)">
              <PotentialCard
                control={control}
                watch={watch}
                setValue={setValue}
                errors={formState.errors}
              />
            </Section>
            <Section value="couplings" title="GB / CS couplings">
              <CouplingsCard control={control} watch={watch} setValue={setValue} />
            </Section>
            <Section value="seesaw" title="Seesaw sector">
              <SeesawCard control={control} />
            </Section>
            <Section value="reheating" title="Reheating & precision">
              <ReheatingCard control={control} />
            </Section>
          </Accordion>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={50} minSize={36}>
        <div className="h-full overflow-y-auto px-6 py-5">
          <div className="mx-auto max-w-3xl space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">
                  Configurator preview
                </h2>
                <p className="text-xs text-muted-foreground">
                  V(ψ) chart sits inside the Potential card on the left.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <CostBadge config={deferred} />
                <ValidityLight result={validity} />
              </div>
            </div>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  F1 — primary mechanism
                </CardTitle>
              </CardHeader>
              <CardContent>
                <EquationBlock copyable latex={f1Latex} />
              </CardContent>
            </Card>
          </div>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={22} minSize={18} maxSize={32}>
        <div className="h-full overflow-y-auto p-4 text-xs text-muted-foreground">
          <p>
            Actions rail intentionally stubbed in QA mode — drag the handles
            and watch the V(ψ) badge update.
          </p>
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}

function Section({
  value,
  title,
  children,
}: {
  value: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <AccordionItem value={value} className="overflow-hidden rounded-md border bg-card">
      <AccordionTrigger className="px-3 py-2 text-sm font-medium hover:no-underline">
        {title}
      </AccordionTrigger>
      <AccordionContent className="border-t bg-background px-3 py-3">
        {children}
      </AccordionContent>
    </AccordionItem>
  );
}
