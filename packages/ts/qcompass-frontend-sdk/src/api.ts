/**
 * Types read from the compute API's OpenAPI document (P4-02).
 *
 * `./generated/openapi.ts` is produced by `scripts/gen_sdk_types.sh` from
 * `ucgle_f1.m8_agent.server.build_app().openapi()`; CI fails when it is
 * stale. Never edit the generated file; change the backend's response
 * models and regenerate.
 */
import type { components, paths } from "./generated/openapi";

export type { components, paths };

/** Every named schema in the API's OpenAPI document. */
export type Schemas = components["schemas"];

type Method = "get" | "post" | "delete";

type SuccessOf<R> = R extends { 200: infer X }
  ? X
  : R extends { 201: infer X }
    ? X
    : R extends { 202: infer X }
      ? X
      : never;

/** The JSON body of a route's 2xx response, e.g. `JsonResponse<"/api/benchmarks", "get">`. */
export type JsonResponse<P extends keyof paths, M extends Method> = paths[P][M] extends {
  responses: infer R;
}
  ? SuccessOf<R> extends { content: { "application/json": infer B } }
    ? B
    : never
  : never;

/** The JSON request body of a route, when the API declares one. */
export type JsonRequest<P extends keyof paths, M extends Method> = paths[P][M] extends {
  requestBody: { content: { "application/json": infer B } };
}
  ? B
  : paths[P][M] extends { requestBody?: { content: { "application/json": infer B } } }
    ? B
    : never;
