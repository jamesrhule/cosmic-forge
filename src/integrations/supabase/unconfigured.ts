/**
 * Stand-in Supabase client used when the project's Supabase variables are
 * missing (PLAN.md R9). It reports `BLOCKED-ON-JAMES:<VAR>` once and lets the
 * app keep running: every query and auth call resolves the way supabase-js
 * reports a failure (`{ data, error }`), never throws, and never points at a
 * default project.
 *
 * Shape notes:
 * - any property access or call returns another stand-in, so builder chains
 *   (`from().select().eq()`), realtime (`channel().on().subscribe()`) and
 *   `onAuthStateChange(...).data.subscription.unsubscribe()` all work;
 * - awaiting a stand-in resolves `{ data, error }`; under `auth` the data is
 *   `{ session: null, user: null }` so session checks see "signed out".
 */
export interface BlockedError {
  name: "SupabaseNotConfigured";
  message: string;
  code: string;
  status: 503;
}

const warned = new Set<string>();

export function blockedMessage(missing: string[]): string {
  return missing.map((v) => `BLOCKED-ON-JAMES:${v}`).join(" ");
}

function makeStandIn(path: string[], error: BlockedError): unknown {
  const target = function standIn() {};
  return new Proxy(target, {
    get(_t, prop) {
      if (prop === "then") {
        const data = path[0] === "auth" ? { session: null, user: null } : null;
        const result = { data, error, count: null, status: 503, statusText: error.message };
        return (onFulfilled?: (v: unknown) => unknown, onRejected?: (e: unknown) => unknown) =>
          Promise.resolve(result).then(onFulfilled, onRejected);
      }
      if (prop === Symbol.toPrimitive) return () => error.message;
      if (typeof prop === "symbol") return undefined;
      return makeStandIn([...path, prop], error);
    },
    apply() {
      return makeStandIn(path, error);
    },
  });
}

export function unconfiguredClient<T>(missing: string[]): T {
  const message = blockedMessage(missing);
  if (!warned.has(message)) {
    warned.add(message);
    console.warn(`[supabase] ${message} — backend features are disabled until it is set.`);
  }
  const error: BlockedError = {
    name: "SupabaseNotConfigured",
    message,
    code: "BLOCKED_ON_JAMES",
    status: 503,
  };
  return makeStandIn([], error) as T;
}
