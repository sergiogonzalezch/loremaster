/**
 * Gestión del token JWT en sessionStorage.
 *
 * NOTA DE SEGURIDAD (H-13):
 * sessionStorage mitiga la exposición persistente a XSS (el token se pierde al
 * cerrar la pestaña), pero NO elimina el riesgo de exfiltración durante la sesión.
 * La solución definitiva es migrar a cookies HttpOnly + SameSite=Strict,
 * lo cual requiere cambios en backend (setear cookie) y frontend (quitar
 * manejo manual de Authorization header).
 */

const TOKEN_KEY = "lm_auth_token";

/** Obtiene el token JWT almacenado, o null si no existe. */
export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

/** Almacena un token JWT en sessionStorage. */
export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

/** Elimina el token JWT de sessionStorage. */
export function removeToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

/** Verifica si existe un token JWT almacenado. */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}
