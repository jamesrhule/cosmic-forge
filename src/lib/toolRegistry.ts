/**
 * Tool-tier registry — security floor for the assistant tool surface.
 *
 * Classification:
 *  - `read`        : safe, auto-allow. No confirmation, no approval.
 *  - `write`       : state-changing. UI must confirm with a diff before dispatch.
 *  - `destructive` : blocked unless caller has the `admin` role AND a signed
 *                    approval token from the backend (/api/approvals).
 *
 * The classification is duplicated server-side in the FastAPI tool registry.
 * Keeping it identical here lets the UI short-circuit denied calls before
 * they hit the wire and lets us audit denial reasons locally.
 *
 * Add new tools by extending `TOOL_TIERS` only — `requireTier()` and
 * `getToolTier()` derive everything else.
 */

import type { ToolName } from "@/types/domain";

export type ToolTier = "read" | "write" | "destructive";
export type AppRole = "viewer" | "researcher" | "admin";

/**
 * Single source of truth. Every member of `ToolName` MUST appear here —
 * the `satisfies` clause below enforces exhaustiveness at typecheck time.
 */
export const TOOL_TIERS = {
  load_run: "read",
  compare_runs: "read",
  open_benchmark: "read",
  summarize_audit: "read",
  cite_paper: "read",
  plot_overlay: "read",

  start_run: "write",
  suggest_parameters: "write",
  export_report: "write",
} as const satisfies Record<ToolName, ToolTier>;

/**
 * Tools that delete or cancel work. None of the current `ToolName`s are
 * destructive yet, but the policy hooks into this list so future tools
 * (`delete_run`, `cancel_run`, `revoke_share`, etc.) are blocked by default.
 */
export const DESTRUCTIVE_TOOLS = new Set<string>([
  "delete_run",
  "cancel_run",
  "purge_artifacts",
  "revoke_share",
]);

export function getToolTier(tool: string): ToolTier {
  if (tool in TOOL_TIERS) return TOOL_TIERS[tool as ToolName];
  if (DESTRUCTIVE_TOOLS.has(tool)) return "destructive";
  // Unknown tools are treated as destructive — fail closed.
  return "destructive";
}

export interface PermissionDecision {
  allow: boolean;
  /** UI must surface a confirmation dialog before dispatch. */
  requiresConfirmation: boolean;
  /** Backend must mint a signed approval token before dispatch. */
  requiresApproval: boolean;
  /** Reason string shown in the audit log when `allow === false`. */
  reason?: string;
}

/**
 * Decide whether a tool call may proceed for the given role.
 *
 * Roles default to `viewer` (signed-out browsers). The frontend should
 * pass the caller's highest role; the backend re-checks before executing.
 */
export function decidePermission(
  tool: string,
  role: AppRole = "viewer",
): PermissionDecision {
  const tier = getToolTier(tool);

  if (tier === "destructive") {
    return {
      allow: role === "admin",
      requiresConfirmation: true,
      requiresApproval: true,
      reason: role === "admin" ? undefined : "destructive tools require admin role",
    };
  }

  if (tier === "write") {
    // Researchers + admins can write; viewers see a confirmation dialog
    // explaining why dispatch is blocked.
    const canWrite = role === "researcher" || role === "admin";
    return {
      allow: canWrite,
      requiresConfirmation: true,
      requiresApproval: false,
      reason: canWrite ? undefined : "write tools require researcher role",
    };
  }

  // read
  return {
    allow: true,
    requiresConfirmation: false,
    requiresApproval: false,
  };
}
