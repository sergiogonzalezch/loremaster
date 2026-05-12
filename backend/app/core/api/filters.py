"""Condiciones de filtro reutilizables para consultas de contenido
compartido e imágenes."""

from app.models.db.collection import Collection
from app.models.db.entity import Entity
from app.models.db.entity_content import EntityContent
from app.models.db.image_generation import ImageGeneration, ImageRecord
from app.models.db.user import User
from app.models.enums import ContentStatus

_CONTENT_CONDITIONS = (
    EntityContent.is_shared.is_(True),
    EntityContent.is_deleted.is_(False),
    EntityContent.status == ContentStatus.confirmed,
    Entity.is_deleted.is_(False),
    Collection.is_deleted.is_(False),
    User.is_deleted.is_(False),
)
"""Condiciones para filtrar contenidos compartidos activos."""

_IMAGE_CONDITIONS = (
    ImageRecord.is_shared.is_(True),
    ImageRecord.is_deleted.is_(False),
    ImageGeneration.is_deleted.is_(False),
    Entity.is_deleted.is_(False),
    Collection.is_deleted.is_(False),
    User.is_deleted.is_(False),
)
"""Condiciones para filtrar imágenes compartidas activas."""
