import { apiFetch } from "./apiClient";

interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface Credentials {
  username: string;
  password: string;
}

export function login(credentials: Credentials): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function register(credentials: Credentials): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}
