import { z } from "zod";
import { FEATURES } from "@/config/features";
import { rjsfFormReachable } from "@/lib/csp";

/**
 * zod 4 probes `new Function("")` once, when it builds its first object
 * schema, to decide whether it may compile fast parsers. Under a CSP without
 * 'unsafe-eval' the probe throws and zod falls back to its interpreter, but the
 * browser still reports a CSP violation for it (zod's own note on
 * `allowsEval` says so). Production script-src has no 'unsafe-eval' in builds
 * that cannot render the RJSF configurator form (`rjsfFormReachable`,
 * src/lib/csp.ts), so those builds run zod `jitless`: the same results,
 * without the probe.
 *
 * Side-effect module (listed in package.json `sideEffects`): it must run
 * before any module builds a schema, so it is the first import of
 * src/start.ts (Start's client entry imports that before the router) and of
 * src/router.tsx.
 */
export const ZOD_JITLESS: boolean = !rjsfFormReachable(FEATURES);

if (ZOD_JITLESS) z.config({ jitless: true });
