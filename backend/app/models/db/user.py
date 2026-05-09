from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field as SQLField

from app.core.database.soft_delete import SoftDeleteMixin


class User(SQLModel, SoftDeleteMixin, table=True):
    """Usuario autenticado en la plataforma.

    Attributes:
        id: Identificador único UUID.
        username: Nombre de usuario único.
        hashed_password: Hash de la contraseña (bcrypt).
        email: Correo electrónico único (opcional).
        display_name: Nombre visible públicamente.
        bio: Biografía pública del usuario.
        avatar_path: Ruta de la imagen de perfil.
        is_admin: Indica si el usuario tiene privilegios de administrador.
        token_version: Versión del token (incrementada al hacer logout de todos los dispositivos).
        created_at: Fecha y hora de registro (UTC).
    """

    __tablename__ = "users"

    id: str = SQLField(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        primary_key=True,
        max_length=36,
    )
    username: str = SQLField(index=True, unique=True, max_length=255)
    hashed_password: str = SQLField(max_length=255)
    email: Optional[str] = SQLField(default=None, max_length=255, unique=True)
    display_name: Optional[str] = SQLField(default=None, max_length=100)
    bio: Optional[str] = SQLField(default=None, max_length=500)
    avatar_path: Optional[str] = SQLField(default=None, max_length=500)
    is_admin: bool = SQLField(default=False)
    token_version: int = SQLField(default=0)
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
