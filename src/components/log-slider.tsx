import { Slider } from "@/components/ui/slider";
import { Sci } from "@/components/sci";

export interface LogSliderProps {
  value: number;
  onChange: (v: number) => void;
  /** Minimum value (must be > 0). */
  min?: number;
  /** Maximum value. */
  max?: number;
  steps?: number;
  label?: string;
}

/**
 * Logarithmic slider for ξ-style couplings spanning many decades.
 * The slider track is linear in log10(value).
 */
export function LogSlider({
  value,
  onChange,
  min = 1e-5,
  max = 1,
  steps = 200,
  label,
}: LogSliderProps) {
  const logMin = Math.log10(min);
  const logMax = Math.log10(max);
  const safe = Math.max(value, min);
  const sliderVal = ((Math.log10(safe) - logMin) / (logMax - logMin)) * steps;

  const onSlider = (vals: number[]) => {
    const t = vals[0] / steps;
    const next = 10 ** (logMin + t * (logMax - logMin));
    onChange(next);
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label ?? "log slider"}</span>
        <Sci value={value} sig={3} />
      </div>
      <Slider
        min={0}
        max={steps}
        step={1}
        value={[Math.max(0, Math.min(steps, sliderVal))]}
        onValueChange={onSlider}
      />
      <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
        <span>10^{logMin}</span>
        <span>10^{logMax}</span>
      </div>
    </div>
  );
}
