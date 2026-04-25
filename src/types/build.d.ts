/**
 * Build-time constants injected by Vite `define` (see vite.config.ts).
 *
 * These are string literals replaced at compile time, NOT runtime
 * values — they survive into the production bundle as plain strings
 * but the SSR/Worker code path never reads `process.env` for them.
 */
declare const __APP_COMMIT__: string;
declare const __APP_BUILD_DATE__: string;
