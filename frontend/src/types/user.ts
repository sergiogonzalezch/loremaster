export interface UserProfile {
  id: string;
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface UpdateProfileRequest {
  display_name?: string | null;
  bio?: string | null;
  avatar_url?: string | null;
  email?: string | null;
}

export interface PublicCollectionSummary {
  id: string;
  name: string;
  description: string;
}

export interface PublicProfile {
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  public_collections: PublicCollectionSummary[];
}

export interface UserAdminRecord {
  id: string;
  username: string;
  email: string | null;
  display_name: string | null;
  is_admin: boolean;
  is_deleted: boolean;
  created_at: string;
}
