/**
 * String tension / breaking (HEP).
 *
 * Merged panel (P0-02): router-branch current-frame readout (value,
 * phase, tension bar, "string breaking" badge when the frame's phase is
 * `string_break`) plus the agent-branch σ(τ) trace with a current-τ
 * marker when the whole timeline is supplied.
 */
import type { HepFrame } from "../types";
import { PanelShell } from "../PanelShell";

export interface StringBreakingAnimProps {
  frame: HepFrame | null;
  frames?: HepFrame[];
}

export function StringBreakingAnim({ frame, frames = [] }: StringBreakingAnimProps) {
  const tension = frame?.string_tension ?? 0;
  const phase = frame?.phase || "—";
  const broken = phase === "string_break";
  // Bar scale: the trace peak when the timeline is known, else the
  // router-branch fixed scale (σ = 0.5 fills the bar).
  const peak = frames.length > 0 ? Math.max(1e-9, ...frames.map((f) => f.string_tension)) : 0.5;

  return (
    <PanelShell
      title="String tension / breaking"
      empty={!frame}
      bodyClassName="flex flex-col items-center justify-center gap-2 p-3"
      caption={
        frames.length > 0 ? (
          <>
            σ(τ) over {frames.length} frames · peak {peak.toFixed(3)}
          </>
        ) : null
      }
    >
      <div className="font-mono text-2xl tabular-nums">{tension.toFixed(3)}</div>
      <div className="text-[11px] text-muted-foreground">
        phase: <span className="font-mono">{phase}</span>
      </div>
      <div className="h-2 w-3/4 overflow-hidden rounded-full bg-muted">
        <div
          className={"h-full transition-all " + (broken ? "bg-amber-500" : "bg-primary")}
          style={{ width: `${Math.min(100, Math.max(0, (tension / peak) * 100))}%` }}
        />
      </div>
      {broken ? (
        <div className="rounded-md bg-amber-500/10 px-2 py-1 text-[11px] text-amber-700 dark:text-amber-400">
          string breaking event
        </div>
      ) : null}
      {frames.length > 1 ? <TensionTrace frames={frames} currentTau={frame?.tau} /> : null}
    </PanelShell>
  );
}

function TensionTrace({ frames, currentTau }: { frames: HepFrame[]; currentTau?: number }) {
  const W = 300;
  const H = 60;
  const taus = frames.map((f) => f.tau);
  const minT = Math.min(...taus);
  const spanT = Math.max(1e-9, Math.max(...taus) - minT);
  const maxV = Math.max(1e-9, ...frames.map((f) => f.string_tension));
  const path = frames
    .map((f, i) => {
      const x = ((f.tau - minT) / spanT) * W;
      const y = H - (f.string_tension / maxV) * H;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
  const cx = currentTau === undefined ? null : ((currentTau - minT) / spanT) * W;
  return (
    <svg
      viewBox={`0 -2 ${W} ${H + 4}`}
      className="h-16 w-full"
      role="img"
      aria-label="String breaking"
    >
      <path d={path} fill="none" stroke="hsl(28 90% 55%)" strokeWidth={1.6} />
      {cx !== null ? (
        <line x1={cx} y1={0} x2={cx} y2={H} stroke="hsl(220 70% 50%)" strokeDasharray="4 2" />
      ) : null}
    </svg>
  );
}

export default StringBreakingAnim;
