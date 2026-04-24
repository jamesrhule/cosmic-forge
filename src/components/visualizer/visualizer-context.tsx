import { createContext, useContext } from "react";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

/**
 * The "master" timeline (A) is shared via context so partner components
 * (the B-side particle field, sync-by-phase mappers) can resolve it
 * without prop-drilling through the panel grid.
 *
 * `null` is the legitimate idle value; consumers must handle it.
 */
export const VisualizerMasterContext = createContext<BakedVisualizationTimeline | null>(null);

export function useVisualizerMaster(): BakedVisualizationTimeline | null {
  return useContext(VisualizerMasterContext);
}
