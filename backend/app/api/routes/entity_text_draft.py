# backend/app/api/routes/entity_drafts.py

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_valid_collection
from app.database import get_session
from app.models.collections import Collection
from app.models.common import SuccessResponse
from app.models.entity_text_draft import (
    GenerateEntityTextDraftRequest,
    UpdateEntityTextDraftContentRequest,
    EntityTextDraftResponse,
    EntityTextDraftListResponse,
)
from app.models.entities import EntityResponse
from app.services.entity_text_draft_service import (
    generate_draft_service,
    list_drafts_service,
    update_draft_content_service,
    confirm_draft_service,
    discard_draft_service,
)
from fastapi import HTTPException

router = APIRouter(prefix="/collections", tags=["entity-drafts"])


@router.post(
    "/{collection_id}/entities/{entity_id}/generate",
    response_model=EntityTextDraftResponse,
    status_code=201,
)
async def generate_draft(
    collection_id: str,
    entity_id: str,
    request: GenerateEntityTextDraftRequest,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    return await generate_draft_service(session, entity_id, collection_id, request)


@router.get(
    "/{collection_id}/entities/{entity_id}/drafts",
    response_model=EntityTextDraftListResponse,
)
async def list_drafts(
    collection_id: str,
    entity_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    drafts = list_drafts_service(session, entity_id, collection_id)
    return EntityTextDraftListResponse(data=drafts, count=len(drafts))


@router.patch(
    "/{collection_id}/entities/{entity_id}/drafts/{draft_id}",
    response_model=EntityTextDraftResponse,
)
async def update_draft(
    collection_id: str,
    entity_id: str,
    draft_id: str,
    request: UpdateEntityTextDraftContentRequest,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    draft = update_draft_content_service(session, draft_id, entity_id, request.content)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post(
    "/{collection_id}/entities/{entity_id}/drafts/{draft_id}/confirm",
    response_model=EntityResponse,
)
async def confirm_draft(
    collection_id: str,
    entity_id: str,
    draft_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    entity = confirm_draft_service(session, draft_id, entity_id, collection_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Draft not found")
    return entity


@router.delete(
    "/{collection_id}/entities/{entity_id}/drafts/{draft_id}",
    response_model=SuccessResponse,
)
async def discard_draft(
    collection_id: str,
    entity_id: str,
    draft_id: str,
    collection: Collection = Depends(get_valid_collection),
    session: Session = Depends(get_session),
):
    success = discard_draft_service(session, draft_id, entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"message": f"Draft {draft_id} discarded"}
