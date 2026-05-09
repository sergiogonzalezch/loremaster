import { apiFetch } from "./apiClient";
import { buildQuery } from "./query";
import type { UserAdminRecord } from "../types/user";

export interface AdminMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface AdminUsersResponse {
  data: UserAdminRecord[];
  meta: AdminMeta;
}

export function getAdminUsers(
  params: { page?: number; page_size?: number } = {},
): Promise<AdminUsersResponse> {
  return apiFetch<AdminUsersResponse>(`/admin/users${buildQuery(params)}`);
}

export function adminDeleteUser(userId: string): Promise<void> {
  return apiFetch<void>(`/admin/users/${userId}`, { method: "DELETE" });
}

export function adminDeleteCollection(collectionId: string): Promise<void> {
  return apiFetch<void>(`/admin/collections/${collectionId}`, {
    method: "DELETE",
  });
}
