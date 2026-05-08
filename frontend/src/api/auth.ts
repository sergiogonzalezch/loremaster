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

export function login(credentials: LoginCredentials): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function register(
  credentials: RegisterCredentials,
): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}
