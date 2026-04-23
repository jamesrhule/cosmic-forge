import type { Control, FieldErrors, UseFormSetValue, UseFormWatch } from "react-hook-form";
import { Controller } from "react-hook-form";
import {
  RadioGroup,
  RadioGroupItem,
} from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { ClientOnly } from "@/components/client-only";
import { PotentialEditor } from "@/components/potential-editor";
import { PotentialPreviewChart } from "@/components/potential-preview-chart";
import { SciInput } from "@/components/sci-input";
import { defaultsForPotential, DEFAULT_CUSTOM_PYTHON } from "@/lib/configDefaults";
import type { PotentialKind, RunConfig } from "@/types/domain";

const KINDS: Array<{ value: PotentialKind; label: string; hint: string }> = [
  { value: "starobinsky", label: "Starobinsky R²", hint: "Single mass M" },
  { value: "natural", label: "Natural inflation", hint: "f, Λ⁴" },
  { value: "hilltop", label: "Hilltop", hint: "μ, p" },
  { value: "custom", label: "Custom (Python)", hint: "Define V(ψ)" },
];

export interface PotentialCardProps {
  control: Control<RunConfig>;
  watch: UseFormWatch<RunConfig>;
  setValue: UseFormSetValue<RunConfig>;
  errors: FieldErrors<RunConfig>;
}

export function PotentialCard({ control, watch, setValue, errors }: PotentialCardProps) {
  const kind = watch("potential.kind");
  const params = watch("potential.params");
  const customPython = watch("potential.customPython");

  return (
    <div className="space-y-4">
      <Controller
        control={control}
        name="potential.kind"
        render={({ field }) => (
          <RadioGroup
            value={field.value}
            onValueChange={(next) => {
              const k = next as PotentialKind;
              field.onChange(k);
              setValue("potential.params", defaultsForPotential(k), {
                shouldValidate: true,
                shouldDirty: true,
              });
              if (k === "custom" && !customPython) {
                setValue("potential.customPython", DEFAULT_CUSTOM_PYTHON, {
                  shouldDirty: true,
                });
              }
            }}
            className="grid grid-cols-2 gap-2"
          >
            {KINDS.map((k) => (
              <Label
                key={k.value}
                htmlFor={`potkind-${k.value}`}
                className="flex cursor-pointer items-start gap-2 rounded-md border bg-background p-2 text-xs has-[:checked]:border-primary has-[:checked]:bg-accent"
              >
                <RadioGroupItem id={`potkind-${k.value}`} value={k.value} className="mt-0.5" />
                <span>
                  <span className="block font-medium">{k.label}</span>
                  <span className="block text-[10px] text-muted-foreground">{k.hint}</span>
                </span>
              </Label>
            ))}
          </RadioGroup>
        )}
      />

      {kind !== "custom" && (
        <div className="space-y-2">
          {Object.keys(params).map((key) => (
            <ParamRow
              key={`${kind}-${key}`}
              name={key}
              value={params[key] ?? 0}
              invalid={Boolean(errors.potential?.params)}
              onChange={(v) =>
                setValue(`potential.params.${key}` as `potential.params.${string}`, v, {
                  shouldDirty: true,
                  shouldValidate: true,
                })
              }
            />
          ))}
        </div>
      )}

      {kind === "custom" && (
        <ClientOnly
          fallback={
            <div className="h-[240px] rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
              Loading editor…
            </div>
          }
        >
          <PotentialEditor
            value={customPython ?? DEFAULT_CUSTOM_PYTHON}
            onChange={(next) =>
              setValue("potential.customPython", next, { shouldDirty: true })
            }
          />
        </ClientOnly>
      )}

      <div>
        <div className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
          V(ψ) preview
        </div>
        <PotentialPreviewChart kind={kind} params={params} />
      </div>
    </div>
  );
}

function ParamRow({
  name,
  value,
  onChange,
  invalid,
}: {
  name: string;
  value: number;
  onChange: (v: number) => void;
  invalid?: boolean;
}) {
  return (
    <div className="grid grid-cols-[80px_1fr] items-center gap-2">
      <Label className="font-mono text-xs text-muted-foreground" htmlFor={`pp-${name}`}>
        {name}
      </Label>
      <SciInput id={`pp-${name}`} value={value} onChange={onChange} invalid={invalid} />
    </div>
  );
}
