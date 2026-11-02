/**
 * Re-export shim for `getManifestSchema` (PROMPT 4 v2).
 *
 * v2 §TASK 3 names the helper file `src/services/qcompass/manifest.ts`,
 * but the on-disk implementation predates v2 at
 * `manifestSchema.ts`. This shim makes both import paths work
 * without renaming the v1 file (which would break PROMPT 4 v1's
 * existing call sites).
 *
 * Logged conflict: v2 path is `manifest.ts`; on-disk is
 * `manifestSchema.ts`. Resolution: ship both via re-export rather
 * than rename.
 */

export { getManifestSchema } from "./manifestSchema";
