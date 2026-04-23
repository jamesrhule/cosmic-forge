import type { ReactNode } from "react";
import { useIsMounted } from "@/hooks/use-is-mounted";

/**
 * Renders children only after client-side hydration. Useful for components
 * that touch `window` or load browser-only modules (CodeMirror, etc.).
 */
export function ClientOnly({
  children,
  fallback = null,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const mounted = useIsMounted();
  if (!mounted) return <>{fallback}</>;
  return <>{children}</>;
}
