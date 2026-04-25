import { Skeleton } from "@/components/ui/skeleton";

/**
 * Pending fallbacks for TanStack Router `pendingComponent`. Each
 * skeleton mirrors the gross structure of the route it replaces so the
 * page doesn't visually jump when the loader resolves. They render
 * inside the matched route shell, NOT the root, so the existing header
 * stays in place — these only fill the `<Outlet />` body.
 *
 * All skeletons honour `prefers-reduced-motion` via the shared
 * `Skeleton` primitive (which uses `animate-pulse` — Tailwind v4's
 * `motion-reduce:animate-none` rule disables it automatically).
 */

/** Configurator (`/`) — three resizable columns. */
export function ConfiguratorSkeleton() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading configurator"
      className="flex min-h-[calc(100vh-3.5rem-2.5rem)] gap-2 p-2"
      data-testid="configurator-skeleton"
    >
      <div className="hidden w-[28%] flex-col gap-2 lg:flex">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
      <div className="flex flex-1 flex-col gap-3 px-2">
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
      <div className="hidden w-[22%] flex-col gap-2 lg:flex">
        <Skeleton className="h-9 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    </div>
  );
}

/** Visualizer index (`/visualizer`) — card grid. */
export function VisualizerIndexSkeleton() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading runs"
      className="mx-auto max-w-5xl px-6 py-8"
      data-testid="visualizer-index-skeleton"
    >
      <Skeleton className="mb-2 h-5 w-56" />
      <Skeleton className="mb-6 h-3 w-3/4" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    </div>
  );
}

/** Visualizer run (`/visualizer/$runId`) — six-panel grid + transport bar. */
export function VisualizerRunSkeleton() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading visualization"
      className="flex h-[calc(100vh-3.5rem)] min-h-0 flex-col gap-2 p-2"
      data-testid="visualizer-run-skeleton"
    >
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-48" />
        <div className="flex gap-2">
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-7 w-20" />
        </div>
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-1 grid-rows-6 gap-2 sm:grid-cols-2 sm:grid-rows-3 lg:grid-cols-3 lg:grid-rows-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-full w-full" />
        ))}
      </div>
      <Skeleton className="h-10 w-full" />
    </div>
  );
}
