import { cn } from "@/lib/utils";

/**
 * Inline brand mark — orbital ring with a glowing particle. Used in
 * 404, error, and chrome surfaces so the recovery UI feels like the
 * app and not a stack-trace dump.
 */
export function BrandMark({
  size = 64,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      role="img"
      aria-label="UCGLE-F1 Workbench"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("text-primary", className)}
    >
      <defs>
        <radialGradient id="brand-particle" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle
        cx="32"
        cy="32"
        r="24"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeOpacity="0.8"
      />
      <ellipse
        cx="32"
        cy="32"
        rx="24"
        ry="9"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeOpacity="0.35"
        transform="rotate(-25 32 32)"
      />
      <circle cx="32" cy="32" r="6" fill="url(#brand-particle)" />
      <circle cx="32" cy="32" r="2" fill="currentColor" />
    </svg>
  );
}
