import { apiGet, apiDelete, buildQuery } from "./factory";
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
  return apiGet<AdminUsersResponse>(`/admin/users${buildQuery(params)}`);
}

export function adminDeleteUser(userId: string): Promise<void> {
  return apiDelete<void>(`/admin/users/${userId}`);
}

export function adminDeleteCollection(collectionId: string): Promise<void> {
  return apiDelete<void>(`/admin/collections/${collectionId}`);
}
