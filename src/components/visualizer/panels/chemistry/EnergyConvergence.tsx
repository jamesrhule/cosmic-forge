import { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import type { ChemistryFrame } from "@/types/manifest";

export interface EnergyConvergenceProps {
  frame: ChemistryFrame | null;
}

export function EnergyConvergence({ frame }: EnergyConvergenceProps) {
  const data = useMemo(() => {
    const series = frame?.energy_convergence ?? [];
    return series.map((e, i) => ({ iter: i, energy: e }));
  }, [frame]);

  if (data.length === 0) {
    return <PanelBody title="SCF energy convergence" empty />;
  }

  return (
    <PanelBody title="SCF energy convergence">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 16, right: 16, bottom: 16, left: 32 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <XAxis
            dataKey="iter"
            stroke="currentColor"
            fontSize={11}
            tickLine={false}
            label={{ value: "iteration", position: "insideBottom", offset: -2, fontSize: 10 }}
          />
          <YAxis
            stroke="currentColor"
            fontSize={11}
            tickLine={false}
            label={{ value: "E (Hartree)", angle: -90, position: "insideLeft", fontSize: 10 }}
          />
          <Tooltip
            cursor={{ stroke: "currentColor", strokeOpacity: 0.2 }}
            contentStyle={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              borderRadius: 6,
            }}
          />
          <Line type="monotone" dataKey="energy" stroke="hsl(var(--primary))" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </PanelBody>
  );
}

function PanelBody({
  title,
  empty,
  children,
}: {
  title: string;
  empty?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        {title}
      </div>
      <div className="min-h-0 flex-1 p-2">
        {empty ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
