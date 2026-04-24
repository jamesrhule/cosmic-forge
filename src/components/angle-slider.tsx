import { Slider } from "@/components/ui/slider";

export interface AngleSliderProps {
  value: number;
  onChange: (v: number) => void;
  label?: string;
}

/** 0..2π slider with degree readout. */
export function AngleSlider({ value, onChange, label }: AngleSliderProps) {
  const degrees = (value * 180) / Math.PI;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label ?? "angle"}</span>
        <span className="font-mono tabular-nums">
          {value.toFixed(3)} rad{" "}
          <span className="text-muted-foreground">({degrees.toFixed(1)}°)</span>
        </span>
      </div>
      <Slider
        min={0}
        max={2 * Math.PI}
        step={Math.PI / 180}
        value={[Math.max(0, Math.min(2 * Math.PI, value))]}
        onValueChange={(vals) => onChange(vals[0])}
      />
      <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
        <span>0</span>
        <span>π/2</span>
        <span>π</span>
        <span>3π/2</span>
        <span>2π</span>
      </div>
    </div>
  );
}
