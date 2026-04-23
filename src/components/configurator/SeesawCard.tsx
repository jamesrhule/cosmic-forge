import type { Control } from "react-hook-form";
import { NumericRow } from "@/components/configurator/CouplingsCard";
import type { RunConfig } from "@/types/domain";

export function SeesawCard({ control }: { control: Control<RunConfig> }) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Right-handed neutrino sector. M₁ sets the lightest sterile mass;
        S_E2 is the second sphaleron entropy coefficient. Natural seesaw
        windows: 10⁶–10¹⁶ GeV for M₁, 0.01–0.2 for S_E2.
      </p>
      <NumericRow
        control={control}
        name="couplings.M1"
        label="M₁"
        hint="lightest sterile [GeV]"
      />
      <NumericRow
        control={control}
        name="couplings.S_E2"
        label="S_E2"
        hint="sphaleron coefficient"
      />
    </div>
  );
}
