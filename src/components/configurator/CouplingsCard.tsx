import type { Control, UseFormSetValue, UseFormWatch } from "react-hook-form";
import { Controller } from "react-hook-form";
import { Label } from "@/components/ui/label";
import { LogSlider } from "@/components/log-slider";
import { AngleSlider } from "@/components/angle-slider";
import { SciInput } from "@/components/sci-input";
import type { RunConfig } from "@/types/domain";

export interface CouplingsCardProps {
  control: Control<RunConfig>;
  watch: UseFormWatch<RunConfig>;
  setValue: UseFormSetValue<RunConfig>;
}

export function CouplingsCard({ control, watch, setValue }: CouplingsCardProps) {
  const xi = watch("couplings.xi");
  const theta = watch("couplings.theta_grav");

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label className="text-xs">ξ — GB / CS coupling</Label>
        <LogSlider
          label="log ξ"
          value={Math.max(xi, 1e-6)}
          onChange={(v) =>
            setValue("couplings.xi", v, { shouldDirty: true, shouldValidate: true })
          }
          min={1e-5}
          max={1}
        />
        <Controller
          control={control}
          name="couplings.xi"
          render={({ field, fieldState }) => (
            <SciInput
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              invalid={fieldState.invalid}
            />
          )}
        />
      </div>

      <div className="space-y-2">
        <Label className="text-xs">θ_grav — gravitational CP angle</Label>
        <AngleSlider
          value={theta}
          onChange={(v) =>
            setValue("couplings.theta_grav", v, {
              shouldDirty: true,
              shouldValidate: true,
            })
          }
        />
      </div>

      <NumericRow
        control={control}
        name="couplings.f_a"
        label="f_a"
        hint="axion decay constant [GeV]"
      />
      <NumericRow
        control={control}
        name="couplings.M_star"
        label="M⋆"
        hint="cutoff scale [GeV]"
      />
    </div>
  );
}

function NumericRow({
  control,
  name,
  label,
  hint,
}: {
  control: Control<RunConfig>;
  name:
    | "couplings.f_a"
    | "couplings.M_star"
    | "couplings.M1"
    | "couplings.S_E2"
    | "reheating.Gamma_phi"
    | "reheating.T_reh_GeV";
  label: string;
  hint: string;
}) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <div className="grid grid-cols-[80px_1fr] items-start gap-2">
          <div className="pt-2">
            <Label className="font-mono text-xs">{label}</Label>
            <p className="text-[10px] text-muted-foreground">{hint}</p>
          </div>
          <SciInput
            value={field.value as number}
            onChange={field.onChange}
            onBlur={field.onBlur}
            invalid={fieldState.invalid}
          />
        </div>
      )}
    />
  );
}

export { NumericRow };
