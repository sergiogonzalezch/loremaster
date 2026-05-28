/**
 * Endpoints de autenticación: login, registro y logout.
 */

import { apiFetch } from "./apiClient";

export interface AuthSuccessResponse {
  message: string;
  username: string;
  expires_at?: string | null;
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

/** Inicia sesión y setea cookies de autenticación (HttpOnly + CSRF). */
export function login(
  credentials: LoginCredentials,
): Promise<AuthSuccessResponse> {
  return apiFetch<AuthSuccessResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

/** Registra un nuevo usuario y setea cookies de autenticación. */
export function register(
  credentials: RegisterCredentials,
): Promise<AuthSuccessResponse> {
  return apiFetch<AuthSuccessResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

/** Cierra la sesión del usuario actual (invalida el token en el backend). */
export function logoutApi(): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST" });
}

/** Rota el access token usando el refresh token en cookie HttpOnly. */
export function refreshToken(): Promise<AuthSuccessResponse> {
  return apiFetch<AuthSuccessResponse>("/auth/refresh", { method: "POST" });
}
