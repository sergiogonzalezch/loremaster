/**
 * Endpoints de administración: listar usuarios, eliminar usuarios y colecciones.
 */

import { apiGet, apiDelete, buildQuery } from "./factory";
import type { UserAdminRecord } from "../types/user";

interface AdminMeta {
  page: number;
  page_size: number;
  total: number;
}

interface AdminUsersResponse {
  data: UserAdminRecord[];
  meta: AdminMeta;
}

/** Lista todos los usuarios (solo admin). */
export function getAdminUsers(
  params: { page?: number; page_size?: number } = {},
): Promise<AdminUsersResponse> {
  return apiGet<AdminUsersResponse>(`/admin/users${buildQuery(params)}`);
}

/** Elimina un usuario por ID (soft-delete, solo admin). */
export function adminDeleteUser(userId: string): Promise<void> {
  return apiDelete<void>(`/admin/users/${userId}`);
}
