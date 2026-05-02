/**
 * QCompass — Auth scaffolding store (in-memory).
 *
 * Holds bearer token + selected tenant for `services/qcompass/http.ts`
 * to inject into outgoing requests. NOT real auth — verification happens
 * server-side, behind FEATURES.qcompassAuth, after the backend wires it.
 *
 * @example
 *   import { useAuth } from "@/store/auth";
 *   const tenantId = useAuth(s => s.tenantId);
 */
import { create } from "zustand";

export interface AuthState {
  token: string | null;
  tenantId: string | null;
  setToken: (token: string | null) => void;
  setTenant: (tenantId: string | null) => void;
  signOut: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  token: null,
  tenantId: null,
  setToken: (token) => set({ token }),
  setTenant: (tenantId) => set({ tenantId }),
  signOut: () => set({ token: null, tenantId: null }),
}));

/** Non-React accessor for service modules. */
export function getAuthSnapshot(): { token: string | null; tenantId: string | null } {
  const { token, tenantId } = useAuth.getState();
  return { token, tenantId };
}
