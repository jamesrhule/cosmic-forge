import type { Control } from "react-hook-form";
import { Controller } from "react-hook-form";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { NumericRow } from "@/components/configurator/CouplingsCard";
import type { Precision, RunConfig } from "@/types/domain";

const PRECISIONS: Array<{ value: Precision; label: string; hint: string }> = [
  { value: "fast", label: "Fast", hint: "32³ grid · drafts" },
  { value: "standard", label: "Standard", hint: "64³ grid · papers" },
  { value: "high", label: "High", hint: "128³ grid · benchmarks" },
];

export function ReheatingCard({ control }: { control: Control<RunConfig> }) {
  return (
    <div className="space-y-4">
      <NumericRow
        control={control}
        name="reheating.Gamma_phi"
        label="Γ_φ"
        hint="inflaton decay rate [GeV]"
      />
      <NumericRow
        control={control}
        name="reheating.T_reh_GeV"
        label="T_reh"
        hint="reheating temperature [GeV]"
      />

      <div>
        <Label className="text-xs">Precision</Label>
        <Controller
          control={control}
          name="precision"
          render={({ field }) => (
            <RadioGroup
              value={field.value}
              onValueChange={(v) => field.onChange(v as Precision)}
              className="mt-2 grid grid-cols-3 gap-2"
            >
              {PRECISIONS.map((p) => (
                <Label
                  key={p.value}
                  htmlFor={`prec-${p.value}`}
                  className="flex cursor-pointer flex-col gap-0.5 rounded-md border bg-background px-2 py-1.5 text-center text-xs has-[:checked]:border-primary has-[:checked]:bg-accent"
                >
                  <RadioGroupItem id={`prec-${p.value}`} value={p.value} className="sr-only" />
                  <span className="font-medium">{p.label}</span>
                  <span className="text-[10px] text-muted-foreground">{p.hint}</span>
                </Label>
              ))}
            </RadioGroup>
          )}
        />
      </div>
    </div>
  );
}
