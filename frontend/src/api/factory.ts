/**
 * Helpers tipados para operaciones CRUD sobre la API.
 *
 * Proporciona `apiGet`, `apiPost`, `apiPatch`, `apiDelete` con soporte
 * de query params, trim de strings y abort signals.
 */

import { apiFetch } from "./apiClient";
import { buildQuery } from "./query";
import { trimStringValues } from "../utils/strings";

export { buildQuery } from "./query";

/** Construye una URL con query params a partir de un path base. */
function buildPaginatedPath(
  basePath: string,
  params: Record<string, unknown> = {},
): string {
  return `${basePath}${buildQuery(params)}`;
}

/** GET tipado contra la API. */
export function apiGet<T>(
  path: string,
  _params?: unknown,
  options?: RequestInit,
): Promise<T> {
  const params = _params as Record<string, unknown> | undefined;
  return apiFetch<T>(params ? buildPaginatedPath(path, params) : path, {
    ...options,
    method: "GET",
  });
}

/** POST tipado contra la API. Aplica trim a los valores string del body. */
export function apiPost<T>(
  path: string,
  data?: object,
  options?: RequestInit,
): Promise<T> {
  return apiFetch<T>(path, {
    ...options,
    method: "POST",
    body: data ? JSON.stringify(trimStringValues(data)) : undefined,
  });
}

/** PATCH tipado contra la API. Aplica trim a los valores string del body. */
export function apiPatch<T>(
  path: string,
  data?: object,
  options?: RequestInit,
): Promise<T> {
  return apiFetch<T>(path, {
    ...options,
    method: "PATCH",
    body: data ? JSON.stringify(trimStringValues(data)) : undefined,
  });
}

/** DELETE tipado contra la API. */
export function apiDelete<T = void>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: "DELETE" });
}
