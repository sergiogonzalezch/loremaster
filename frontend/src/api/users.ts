import { apiFetch } from "./apiClient";
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
  return apiFetch<UserProfile>("/users/me");
}

export function updateMyProfile(
  data: UpdateProfileRequest,
): Promise<UserProfile> {
  return apiFetch<UserProfile>("/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function getPublicProfile(username: string): Promise<PublicProfile> {
  return apiFetch<PublicProfile>(
    `/users/${encodeURIComponent(username)}/profile`,
  );
}

export function getPublicFeed(
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<PaginatedResponse<PublicFeedItem>> {
  return apiFetch<PaginatedResponse<PublicFeedItem>>(
    `/public/feed${buildQuery(params)}`,
    { signal },
  );
}

export function getPublicImages(
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<PaginatedResponse<PublicImageItem>> {
  return apiFetch<PaginatedResponse<PublicImageItem>>(
    `/public/images${buildQuery(params)}`,
    { signal },
  );
}

export function getMyAvatar(): Promise<AvatarResponse> {
  return apiFetch<AvatarResponse>("/users/me/avatar");
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
  return apiFetch<void>("/users/me/avatar", { method: "DELETE" });
}
