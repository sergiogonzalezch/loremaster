import { apiFetch } from "./apiClient";
import { buildQuery } from "./query";
import { trimStringValues } from "../utils/strings";

export { buildQuery } from "./query";
export { trimStringValues } from "../utils/strings";

export interface PaginationParams {
  page?: number;
  page_size?: number;
  order?: "asc" | "desc";
}

export interface DateFilterParams {
  created_after?: string;
  created_before?: string;
}

export function buildPath(parts: (string | undefined)[]): string {
  return parts.filter(Boolean).join("/");
}

export function buildPaginatedPath(
  basePath: string,
  params: Record<string, unknown> = {},
): string {
  return `${basePath}${buildQuery(params)}`;
}

export function apiGet<T>(
  path: string,
  _params?: unknown,
  options?: RequestInit,
): Promise<T> {
  const params = _params as Record<string, unknown> | undefined;
  return apiFetch<T>(
    params ? buildPaginatedPath(path, params) : path,
    { ...options, method: "GET" },
  );
}

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

export function apiDelete<T = void>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: "DELETE" });
}
