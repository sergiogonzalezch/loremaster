"""Rutas de autenticación mediante Clerk."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.auth.clerk import decode_clerk_token
from app.database import get_session
from app.models.db.user import User

router = APIRouter(prefix="/auth/clerk", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.get("/verify")
def verify(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[Session, Depends(get_session)],
):
    """Verifica la validez de un token Bearer de Clerk.

    Valida que el usuario exista en la BD y no esté eliminado.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
        )
    payload = decode_clerk_token(credentials.credentials)
    user_id = payload.get("sub")
    user = session.get(User, user_id)
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    return {"valid": True, "user_id": user_id}
