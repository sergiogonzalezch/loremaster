from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.valid_collection import get_entity_or_404
from app.database import get_session
from app.models.entities import Entity, EntityResponse
from app.models.entity_text_draft import (
    GenerateEntityTextDraftRequest,
    UpdateEntityTextDraftContentRequest,
    EntityTextDraftResponse,
    EntityTextDraftListResponse,
)
from app.services.entity_text_draft_service import (
    generate_draft_service,
    list_drafts_service,
    update_draft_content_service,
    confirm_draft_service,
    discard_draft_service,
)

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
    entity: Entity = Depends(get_entity_or_404),
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
    entity: Entity = Depends(get_entity_or_404),
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
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    draft = update_draft_content_service(
        session, draft_id, entity_id, collection_id, request.content
    )
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
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    result = confirm_draft_service(session, draft_id, entity_id, collection_id)
    if not result:
        raise HTTPException(status_code=404, detail="Draft not found")
    return result


@router.delete(
    "/{collection_id}/entities/{entity_id}/drafts/{draft_id}",
    response_model=EntityTextDraftResponse,
)
async def discard_draft(
    collection_id: str,
    entity_id: str,
    draft_id: str,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    draft = discard_draft_service(session, draft_id, entity_id, collection_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft
