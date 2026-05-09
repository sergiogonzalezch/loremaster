/**
 * Endpoints de usuarios: perfil propio, perfiles públicos, feed público y avatar.
 */

import { apiFetch } from "./apiClient";
import { apiGet, apiPatch, apiDelete, buildQuery } from "./factory";
import type {
  UserProfile,
  UpdateProfileRequest,
  PublicProfile,
  PublicFeedItem,
  PublicImageItem,
  AvatarResponse,
} from "../types/user";
import type { PaginatedResponse } from "../types";

/** Obtiene el perfil del usuario autenticado. */
export function getMyProfile(): Promise<UserProfile> {
  return apiGet<UserProfile>("/users/me");
}

/** Actualiza el perfil del usuario autenticado. */
export function updateMyProfile(
  data: UpdateProfileRequest,
): Promise<UserProfile> {
  return apiPatch<UserProfile>("/users/me", data);
}

/** Obtiene el perfil público de un usuario por su nombre de usuario. */
export function getPublicProfile(username: string): Promise<PublicProfile> {
  return apiGet<PublicProfile>(
    `/users/${encodeURIComponent(username)}/profile`,
  );
}

/** Obtiene el feed público de contenidos compartidos. */
export function getPublicFeed(
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<PaginatedResponse<PublicFeedItem>> {
  return apiGet<PaginatedResponse<PublicFeedItem>>(
    `/public/feed${buildQuery(params)}`,
    undefined,
    { signal },
  );
}

/** Obtiene el feed público de imágenes compartidas. */
export function getPublicImages(
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<PaginatedResponse<PublicImageItem>> {
  return apiGet<PaginatedResponse<PublicImageItem>>(
    `/public/images${buildQuery(params)}`,
    undefined,
    { signal },
  );
}

/** Obtiene la información del avatar del usuario autenticado. */
export function getMyAvatar(): Promise<AvatarResponse> {
  return apiGet<AvatarResponse>("/users/me/avatar");
}

/** Sube una nueva imagen de avatar para el usuario autenticado. */
export function uploadMyAvatar(file: File): Promise<AvatarResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<AvatarResponse>("/users/me/avatar", {
    method: "POST",
    body: formData,
  });
}

/** Elimina el avatar del usuario autenticado. */
export function deleteMyAvatar(): Promise<void> {
  return apiDelete<void>("/users/me/avatar");
}
