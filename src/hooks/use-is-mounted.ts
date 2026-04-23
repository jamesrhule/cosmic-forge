import { useEffect, useState } from "react";

/**
 * Returns true once the component has mounted on the client. Useful for
 * gating browser-only code (CodeMirror, window-dependent measurements)
 * during SSR.
 */
export function useIsMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}
