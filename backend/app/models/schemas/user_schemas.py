from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """Respuesta básica con los datos públicos de un usuario.

    Attributes:
        id: Identificador único.
        username: Nombre de usuario.
        created_at: Fecha de registro.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    created_at: datetime


class UserProfileResponse(BaseModel):
    """Respuesta completa del perfil del usuario autenticado.

    Attributes:
        id: Identificador único.
        username: Nombre de usuario.
        email: Correo electrónico.
        display_name: Nombre visible públicamente.
        bio: Biografía.
        avatar_url: URL de la imagen de perfil.
        is_admin: Si el usuario es administrador.
        created_at: Fecha de registro.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    is_admin: bool = False
    created_at: datetime


class UserAdminResponse(BaseModel):
    """Respuesta de perfil para administradores con información extendida.

    Attributes:
        id: Identificador único.
        username: Nombre de usuario.
        email: Correo electrónico.
        display_name: Nombre visible.
        bio: Biografía.
        avatar_url: URL del avatar.
        is_admin: Si el usuario es administrador.
        is_deleted: Si el usuario está eliminado (soft-delete).
        created_at: Fecha de registro.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    is_admin: bool
    is_deleted: bool
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    """Esquema para actualizar el perfil del usuario.

    Attributes:
        display_name: Nuevo nombre visible (opcional).
        bio: Nueva biografía (opcional).
        email: Nuevo correo electrónico (opcional).
    """

    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    email: EmailStr | None = Field(default=None, max_length=255)


class AvatarResponse(BaseModel):
    """Respuesta tras subir o eliminar la imagen de perfil.

    Attributes:
        avatar_url: URL de la imagen o None si no hay avatar.
        has_avatar: Indica si el usuario tiene avatar configurado.
    """

    avatar_url: str | None
    has_avatar: bool
