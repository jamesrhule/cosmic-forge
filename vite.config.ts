// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - tanstackStart, viteReact, tailwindcss, tsConfigPaths, cloudflare (build-only),
//     componentTagger (dev-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... } }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

/**
 * Vendor chunk splitting.
 *
 * The default Vite output buckets `react-katex`, `recharts`, and the
 * three.js / R3F surface together with the route bundle, which makes
 * the initial route's chunk graph noisier than it needs to be. This
 * keeps each heavy vendor in its own cacheable chunk so the
 * Configurator route doesn't pay for KaTeX + Recharts + Three until
 * the visualizer route is actually navigated to.
 */
function manualChunks(id: string): string | undefined {
  if (!id.includes("node_modules")) return undefined;
  if (id.includes("/katex/")) return "vendor-katex";
  if (id.includes("/recharts/") || id.includes("victory-vendor")) return "vendor-recharts";
  if (id.includes("/three/") || id.includes("@react-three")) return "vendor-three";
  return undefined;
}

/**
 * Build-time version stamp surfaced in the footer / about chip.
 *
 * Resolved from common CI env vars first (Cloudflare, Vercel, GitHub),
 * then falls back to a short ISO date so dev builds still render
 * something meaningful instead of `v1.0`.
 */
const COMMIT_SHA: string =
  process.env.CF_PAGES_COMMIT_SHA ??
  process.env.VERCEL_GIT_COMMIT_SHA ??
  process.env.GITHUB_SHA ??
  process.env.COMMIT_SHA ??
  "dev";
const SHORT_SHA = COMMIT_SHA.slice(0, 7);
const BUILD_DATE = new Date().toISOString().slice(0, 10);

export default defineConfig({
  vite: {
    define: {
      __APP_COMMIT__: JSON.stringify(SHORT_SHA),
      __APP_BUILD_DATE__: JSON.stringify(BUILD_DATE),
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks,
        },
      },
    },
  },
});
