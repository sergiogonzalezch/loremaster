from fastapi import APIRouter, Depends, HTTPException, Response
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
    edit_draft_service,
    confirm_draft_service,
    discard_draft_service,
    soft_delete_draft_service,
)

router = APIRouter(prefix="/collections", tags=["entity-drafts"])


@router.post(
    "/{collection_id}/entities/{entity_id}/generate",
    response_model=EntityTextDraftResponse,
    status_code=201,
)
async def generate_draft(
    request: GenerateEntityTextDraftRequest,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    try:
        return generate_draft_service(session, entity, request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get(
    "/{collection_id}/entities/{entity_id}/drafts",
    response_model=EntityTextDraftListResponse,
)
async def list_drafts(
    collection_id: str,
    entity_id: str,
    _: Entity = Depends(get_entity_or_404),
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
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    draft = edit_draft_service(
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
    draft_id: str,
    entity: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    result = confirm_draft_service(session, draft_id, entity)
    if not result:
        raise HTTPException(status_code=404, detail="Draft not found")
    return result


@router.patch(
    "/{collection_id}/entities/{entity_id}/drafts/{draft_id}/discard",
    response_model=EntityTextDraftResponse,
)
async def discard_draft(
    collection_id: str,
    entity_id: str,
    draft_id: str,
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    draft = discard_draft_service(session, draft_id, entity_id, collection_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.delete(
    "/{collection_id}/entities/{entity_id}/drafts/{draft_id}",
    status_code=204,
)
async def delete_draft(
    collection_id: str,
    entity_id: str,
    draft_id: str,
    _: Entity = Depends(get_entity_or_404),
    session: Session = Depends(get_session),
):
    result = soft_delete_draft_service(session, draft_id, entity_id, collection_id)
    if not result:
        raise HTTPException(status_code=404, detail="Draft not found")
    return Response(status_code=204)
