from enum import Enum


class ContentCategory(str, Enum):
    backstory = "backstory"
    extended_description = "extended_description"
    scene = "scene"
    chapter = "chapter"


class ContentStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    discarded = "discarded"