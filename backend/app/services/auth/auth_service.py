"""Lógica de negocio para autenticación de usuarios."""

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.auth import DUMMY_HASH, hash_password, verify_password
from app.models.db.user import User


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
        # Timing-safe dummy check: iguala el tiempo de respuesta cuando el usuario no existe.
        verify_password(password, DUMMY_HASH)
        valid = False

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    return user


def create_user(session: Session, username: str, email: str, password: str) -> User:
    """Registra un nuevo usuario en la base de datos."""
    # username y email tienen UNIQUE a nivel de BD que aplica también a filas
    # soft-deleted; por eso ninguno de los dos checks filtra is_deleted: deben
    # reflejar la constraint real y devolver 400 en vez de un IntegrityError 500.
    if session.exec(select(User).where(User.username == username)).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        )
    if session.exec(select(User).where(User.email == email)).first():
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


def get_or_create_clerk_user(session: Session, payload: dict) -> User:
    """Retorna el User local vinculado al Clerk JWT, creándolo si no existe.

    Orden de lookup:
    1. Por Clerk sub (retorno directo si ya existe).
    2. Por email — fusiona con cuenta local preexistente sin duplicar.
    3. Crea usuario nuevo si no hay coincidencia.
    """
    user_id = payload["sub"]
    user = session.get(User, user_id)
    if user:
        return user

    email = payload.get("email", "")

    if email:
        existing = session.exec(
            select(User).where(User.email == email, User.is_deleted.is_(False))
        ).first()
        if existing:
            return existing

    candidate = payload.get("username") or (email.split("@")[0] if email else None) or user_id
    # user_id (Clerk) es único globalmente — se usa como fallback si el nombre derivado colisiona
    username = candidate if not session.exec(select(User).where(User.username == candidate)).first() else user_id
    user = User(
        id=user_id,
        username=username,
        email=email,
        hashed_password="",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
