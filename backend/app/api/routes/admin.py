from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.core.auth_deps import get_admin_user
from app.core.common import paginate_with_sort
from app.core.query_params import PaginationParams
from app.database import get_session
from app.models.users import User, UserAdminResponse
from app.models.collections import Collection
from app.services.user_image import get_avatar_info

from app.services.collection_service import delete_collection_service
from app.services.deletion_service import cascade_delete_collection

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_all_users(
    pagination: Annotated[PaginationParams, Depends()],
    _: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    users, total = paginate_with_sort(
        session,
        User,
        [],
        page=pagination.page,
        page_size=pagination.page_size,
        order_col=User.created_at,
        order="desc",
    )

    data = [
        UserAdminResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            display_name=u.display_name,
            bio=u.bio,
            avatar_url=get_avatar_info(u)["avatar_url"],
            is_admin=u.is_admin,
            is_deleted=u.is_deleted,
            created_at=u.created_at,
        ).model_dump()
        for u in users
    ]
    return {
        "data": data,
        "meta": {
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total": total,
        },
    }


@router.delete("/collections/{collection_id}", status_code=204)
def admin_delete_collection(
    collection_id: str,
    _: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        return Response(status_code=204)
    delete_collection_service(session, collection)
    return Response(status_code=204)


@router.delete("/users/{user_id}", status_code=204)
def admin_delete_user(
    user_id: str,
    current_admin: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    if user_id == current_admin["sub"]:
        raise HTTPException(
            status_code=403, detail="No puedes eliminar tu propia cuenta"
        )
    user = session.get(User, user_id)
    if not user or user.is_deleted:
        return Response(status_code=204)
    collections = session.exec(
        select(Collection).where(
            Collection.owner_id == user_id,
            Collection.is_deleted == False,
        )
    ).all()
    for collection in collections:
        cascade_delete_collection(session, collection)
    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    return Response(status_code=204)
