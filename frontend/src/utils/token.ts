/**
 * Gestión del token JWT en localStorage.
 */

const TOKEN_KEY = "lm_auth_token";

/** Obtiene el token JWT almacenado, o null si no existe. */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

/** Almacena un token JWT en localStorage. */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

/** Elimina el token JWT de localStorage. */
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/** Verifica si existe un token JWT almacenado. */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}
