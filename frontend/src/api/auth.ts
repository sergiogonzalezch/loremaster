/**
 * Endpoints de autenticación: login, registro y logout.
 */

import { apiFetch } from "./apiClient";

interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface LoginCredentials {
  username_or_email: string;
  password: string;
}

interface RegisterCredentials {
  username: string;
  email: string;
  password: string;
}

/** Inicia sesión y retorna el token JWT. */
export function login(credentials: LoginCredentials): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

/** Registra un nuevo usuario y retorna el token JWT. */
export function register(
  credentials: RegisterCredentials,
): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

/** Cierra la sesión del usuario actual (invalida el token en el backend). */
export function logoutApi(): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST" });
}
