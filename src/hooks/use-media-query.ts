import { useEffect, useState } from "react";

/**
 * SSR-safe `window.matchMedia` wrapper. Returns `false` until mounted,
 * then tracks the query's `matches` value and updates on changes.
 *
 * Use to conditionally render layouts (instead of relying on
 * `hidden lg:block`) so that components inside the inactive branch are
 * truly unmounted — important for libraries like Recharts that warn
 * when measured at 0×0 inside a `display: none` subtree.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia(query);
    const update = () => setMatches(mql.matches);
    update();
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, [query]);

  return matches;
}
