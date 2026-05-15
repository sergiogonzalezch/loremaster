import { apiFetch } from "./apiClient";

/**
 * Intercambia el Clerk JWT por una sesión local (cookies HttpOnly).
 *
 * Se llama una sola vez tras el login con Clerk. El backend valida el JWT,
 * crea o encuentra el usuario local, y setea las cookies de sesión.
 * Todos los requests posteriores usan las cookies automáticamente.
 */
export async function syncClerkSession(clerkToken: string): Promise<void> {
  await apiFetch("/auth/clerk/sync", {
    method: "POST",
    headers: { Authorization: `Bearer ${clerkToken}` },
  });
}
