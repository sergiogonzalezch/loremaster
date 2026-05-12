/**
 * DEPRECADO — Ya no se usa para autenticación.
 *
 * El token JWT ahora se transporta via cookie HttpOnly (H-13, H-14, M-17).
 * Este módulo se mantiene temporalmente por compatibilidad con código
 * legacy, pero no debe usarse en nuevo código.
 *
 * TODO: Eliminar tras verificar que ningún otro módulo lo importa.
 */

const TOKEN_KEY = "lm_auth_token";

/** @deprecated El token ya no se almacena en sessionStorage. */
export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

/** @deprecated El backend setea la cookie HttpOnly directamente. */
export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

/** @deprecated El backend borra la cookie en logout. */
export function removeToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

/** @deprecated Usar el estado del AuthContext en su lugar. */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}
