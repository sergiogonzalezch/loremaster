from sqlalchemy import and_
from sqlalchemy.orm import Query

from app.models.db.entity_content import EntityContent
from app.models.db.image_generation import ImageGeneration, ImageRecord
from app.models.db.entity import Entity
from app.models.db.collection import Collection
from app.models.db.user import User
from app.models.enums import ContentStatus

_CONTENT_CONDITIONS = (
    EntityContent.is_shared == True,
    EntityContent.is_deleted == False,
    EntityContent.status == ContentStatus.confirmed,
    Entity.is_deleted == False,
    Collection.is_deleted == False,
    User.is_deleted == False,
)

_IMAGE_CONDITIONS = (
    ImageRecord.is_shared == True,
    ImageRecord.is_deleted == False,
    ImageGeneration.is_deleted == False,
    Entity.is_deleted == False,
    Collection.is_deleted == False,
    User.is_deleted == False,
)
