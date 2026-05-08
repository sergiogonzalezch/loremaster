import { apiFetch } from "./apiClient";
import type {
  UserProfile,
  UpdateProfileRequest,
  PublicProfile,
} from "../types/user";

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
