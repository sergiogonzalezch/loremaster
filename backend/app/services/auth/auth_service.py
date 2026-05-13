"""Lógica de negocio para autenticación de usuarios."""

from app.core.auth import hash_password, verify_password
from app.models.db.user import User
from fastapi import HTTPException, status
from sqlmodel import Session, select


def authenticate_user(session: Session, username_or_email: str, password: str) -> User:
    """Verifica credenciales y retorna el usuario autenticado."""
    user = session.exec(
        select(User).where(
            (User.username == username_or_email) | (User.email == username_or_email),
            User.is_deleted.is_(False),
        ),
    ).first()

    if user:
        valid = verify_password(password, user.hashed_password)
    else:
        # Timing-safe dummy check: iguala el tiempo de respuesta cuando el usuario no existe (M-6).
        verify_password(password, "$2b$12$abcdefghijklmnopqrstuv")
        valid = False

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    return user


def create_user(session: Session, username: str, email: str, password: str) -> User:
    """Registra un nuevo usuario en la base de datos."""
    if session.exec(select(User).where(User.username == username)).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        )
    if session.exec(
        select(User).where(User.email == email, User.is_deleted.is_(False)),
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado",
        )
    new_user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


def invalidate_session(session: Session, user_id: str) -> None:
    """Incrementa token_version para invalidar tokens previos del usuario."""
    user = session.get(User, user_id)
    if user and not user.is_deleted:
        user.token_version += 1
        session.add(user)
        session.commit()
