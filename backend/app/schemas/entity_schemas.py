from enum import Enum
from pydantic import BaseModel

class EntityType(str, Enum):
    character = "character"
    scene = "scene"
    faction = "faction"
    item = "item"

class CreateEntityRequest(BaseModel):
    type: EntityType
    name: str
    description: str = ""
    attributes: dict = {}

class EntityResponse(BaseModel):
    id: str
    type: EntityType
    name: str
    attributes: dict