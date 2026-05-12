import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.core.api.params import PaginationParams
from app.core.auth.dependencies import get_admin_user
from app.core.database.utils import paginate_with_sort
from app.database import get_session
from app.models.db.collection import Collection
from app.models.db.user import User
from app.models.schemas.user_schemas import UserAdminResponse
from app.services.collection.collection_service import delete_collection_service
from app.services.deletion_service import cascade_delete_collection
from app.services.profile.profile_service import delete_profile_image, get_avatar_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_all_users(
    pagination: Annotated[PaginationParams, Depends()],
    _: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    """Lista todos los usuarios (solo administradores).

    Incluye usuarios eliminados y no eliminados.
    """
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
    current_admin: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    """Elimina una colección en nombre de un usuario (solo administradores).

    Elimina en cascada todos los contenidos. Retorna 204 aunque la colección
    no exista (idempotente).
    """
    collection = session.get(Collection, collection_id)
    if not collection or collection.is_deleted:
        return Response(status_code=204)
    owner_id = collection.owner_id
    delete_collection_service(session, collection)
    logger.info(
        "audit action=admin_delete_collection collection_id=%s owner_id=%s admin_id=%s",
        collection_id,
        owner_id,
        current_admin["sub"],
    )
    return Response(status_code=204)


@router.delete("/users/{user_id}", status_code=204)
def admin_delete_user(
    user_id: str,
    current_admin: dict = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    """Elimina un usuario y todas sus colecciones (solo administradores).

    No permite que un admin se elimine a sí mismo.
    """
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
            Collection.is_deleted.is_(False),
        )
    ).all()
    for collection in collections:
        cascade_delete_collection(session, collection)
    try:
        delete_profile_image(session, user)
    except Exception:
        logger.warning(
            "Failed to delete avatar for user %s during admin deletion", user_id
        )
    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    logger.info(
        "audit action=admin_delete_user user_id=%s admin_id=%s",
        user_id,
        current_admin["sub"],
    )
    return Response(status_code=204)
