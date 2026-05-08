from sqlalchemy import and_
from sqlalchemy.orm import Query

from app.models.entity_content import EntityContent
from app.models.image_generation import ImageGeneration, ImageRecord
from app.models.entities import Entity
from app.models.collections import Collection
from app.models.users import User
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
