import { apiFetch } from "./apiClient";
import { buildQuery } from "./query";
import type {
  UserProfile,
  UpdateProfileRequest,
  PublicProfile,
  PublicFeedItem,
  PublicImageItem,
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
