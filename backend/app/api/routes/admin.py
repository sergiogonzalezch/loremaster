from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.core.auth_deps import get_admin_user
from app.database import get_session
from app.models.users import User, UserAdminResponse
from app.models.collections import Collection
from app.models.shared import PaginatedResponse

router = APIRouter(prefix="/admin", tags=["admin"])


class UserAdminListResponse(PaginatedResponse):
    pass


@router.get("/users")
def list_all_users(
    pagination: Annotated[dict, Depends(lambda: {"page": 1, "page_size": 20})],
    _: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    page = pagination.get("page", 1)
    page_size = pagination.get("page_size", 20)
    skip = (page - 1) * page_size

    total = session.exec(select(func.count()).select_from(User)).one()
    users = session.exec(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(page_size)
    ).all()

    data = [
        UserAdminResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            display_name=u.display_name,
            bio=u.bio,
            avatar_url=u.avatar_url,
            is_admin=u.is_admin,
            is_deleted=u.is_deleted,
            created_at=u.created_at,
        ).model_dump()
        for u in users
    ]
    return {"data": data, "meta": {"page": page, "page_size": page_size, "total": total}}


@router.delete("/collections/{collection_id}", status_code=204)
def admin_delete_collection(
    collection_id: str,
    _: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    collection = session.get(Collection, collection_id)
    if not collection:
        return Response(status_code=204)
    collection.is_deleted = True
    from datetime import datetime, timezone

    collection.deleted_at = datetime.now(timezone.utc)
    session.add(collection)
    session.commit()
    return Response(status_code=204)


@router.delete("/users/{user_id}", status_code=204)
def admin_delete_user(
    user_id: str,
    _: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if not user:
        return Response(status_code=204)
    user.is_deleted = True
    from datetime import datetime, timezone

    user.deleted_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    return Response(status_code=204)