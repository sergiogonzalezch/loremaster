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

export interface SharedContentItem {
  id: string;
  content: string;
  category: string;
  entity_name: string;
  entity_type: string;
  confirmed_at: string | null;
  created_at: string;
}

export interface PublicFeedItem {
  content_id: string;
  content: string;
  content_preview: string;
  category: string;
  entity_name: string;
  entity_type: string;
  owner_username: string;
  owner_display_name: string | null;
  confirmed_at: string | null;
  created_at: string;
}

export interface SharedImageItem {
  id: string;
  generation_id: string;
  image_url: string | null;
  storage_path: string | null;
  seed: number;
  auto_prompt: string;
  final_prompt: string;
  entity_name: string;
  entity_type: string;
  created_at: string;
}

export interface PublicImageItem {
  image_id: string;
  generation_id: string;
  image_url: string | null;
  storage_path: string | null;
  seed: number;
  auto_prompt: string;
  final_prompt: string;
  entity_name: string;
  entity_type: string;
  owner_username: string;
  owner_display_name: string | null;
  created_at: string;
}

export interface PublicProfile {
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  shared_contents: SharedContentItem[];
  shared_images: SharedImageItem[];
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
