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

export function getMyProfile(): Promise<UserProfile> {
  return apiGet<UserProfile>("/users/me");
}

export function updateMyProfile(
  data: UpdateProfileRequest,
): Promise<UserProfile> {
  return apiPatch<UserProfile>("/users/me", data);
}

export function getPublicProfile(username: string): Promise<PublicProfile> {
  return apiGet<PublicProfile>(
    `/users/${encodeURIComponent(username)}/profile`,
  );
}

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

export function getMyAvatar(): Promise<AvatarResponse> {
  return apiGet<AvatarResponse>("/users/me/avatar");
}

export function uploadMyAvatar(file: File): Promise<AvatarResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<AvatarResponse>("/users/me/avatar", {
    method: "POST",
    body: formData,
  });
}

export function deleteMyAvatar(): Promise<void> {
  return apiDelete<void>("/users/me/avatar");
}
