import { apiClient } from "./client";
import type { UserProfile, UpdateProfileRequest } from "../types/user";

export async function getMyProfile(): Promise<UserProfile> {
  const res = await apiClient("/users/me");
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function updateMyProfile(
  data: UpdateProfileRequest
): Promise<UserProfile> {
  const res = await apiClient("/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}