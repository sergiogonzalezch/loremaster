from fastapi import APIRouter

from app.core.config import settings
from app.domain.category_rules import ENTITY_CATEGORY_MAP

router = APIRouter(tags=["metadata"])


@router.get("/entity-categories")
def get_entity_categories() -> dict[str, list[str]]:
    return {k.value: [c.value for c in v] for k, v in ENTITY_CATEGORY_MAP.items()}


@router.get("/limits")
def get_limits() -> dict[str, int]:
    return {"max_pending_contents": settings.max_pending_contents}
