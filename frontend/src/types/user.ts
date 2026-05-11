/**
 * Tipos TypeScript para usuarios, perfiles públicos y administración.
 */

/** Perfil del usuario autenticado. */
export interface UserProfile {
  id: string;
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  is_admin: boolean;
  created_at: string;
}

/** Payload para actualizar el perfil. */
export interface UpdateProfileRequest {
  display_name?: string | null;
  bio?: string | null;
  avatar_url?: string | null;
  email?: string | null;
}

/** Item de contenido compartido en perfil público. */
export interface SharedContentItem {
  id: string;
  content: string;
  category: string;
  entity_name: string;
  entity_type: string;
  confirmed_at: string | null;
  created_at: string;
}

/** Item del feed público de contenidos. */
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

/** Item de imagen compartida en perfil público. */
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

/** Item del feed público de imágenes. */
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

/** Perfil público de un usuario. */
export interface PublicProfile {
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  shared_contents: SharedContentItem[];
  shared_images: SharedImageItem[];
}

/** Respuesta de operaciones de avatar. */
export interface AvatarResponse {
  avatar_url: string | null;
  has_avatar: boolean;
}

/** Registro de usuario para el panel de administración. */
export interface UserAdminRecord {
  id: string;
  username: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  is_admin: boolean;
  is_deleted: boolean;
  created_at: string;
}
