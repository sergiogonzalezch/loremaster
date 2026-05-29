"""Servicios de lógica de negocio para perfiles de usuario y avatares."""

import contextlib
import re
import shutil
from pathlib import Path

from fastapi import UploadFile
from sqlmodel import Session, select

from app.core.api.filters import CONTENT_CONDITIONS, IMAGE_CONDITIONS
from app.core.config import settings
from app.core.database.utils import db_commit
from app.core.exceptions import DuplicateEmailError, UserNotFoundError
from app.core.storage import (
    build_storage_path,
    build_storage_url,
    delete_file,
    generate_unique_filename,
    save_file,
)
from app.core.storage.validator import FileValidator
from app.models.db.collection import Collection
from app.models.db.entity import Entity
from app.models.db.entity_content import EntityContent
from app.models.db.image_generation import ImageGeneration, ImageRecord
from app.models.db.user import User
from app.models.schemas.public import (
    PublicProfileResponse,
    SharedContentSummary,
    SharedImageSummary,
)
from app.models.schemas.user import UpdateProfileRequest


def _get_profile_dir(username: str) -> Path:
    return build_storage_path("users", username, "img", "profile")


def get_avatar_info(user: User) -> dict:
    """Retorna la URL del avatar y si el usuario tiene uno asignado."""
    return {
        "avatar_url": build_storage_url(user.avatar_path),
        "has_avatar": user.avatar_path is not None,
    }


def update_profile(session: Session, user: User, request: UpdateProfileRequest) -> User:
    """Actualiza los campos de perfil del usuario."""
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.bio is not None:
        user.bio = request.bio
    if request.email is not None:
        existing = session.exec(
            select(User).where(
                User.email == request.email,
                User.is_deleted.is_(False),
                User.id != user.id,
            ),
        ).first()
        if existing:
            raise DuplicateEmailError
        user.email = request.email
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_public_profile(session: Session, username: str) -> PublicProfileResponse:
    """Obtiene el perfil público de un usuario con sus contenidos e imágenes compartidos."""
    user = session.exec(
        select(User).where(User.username == username, User.is_deleted.is_(False)),
    ).first()
    if not user:
        raise UserNotFoundError

    content_conditions = (*CONTENT_CONDITIONS, Collection.owner_id == user.id)
    image_conditions = (*IMAGE_CONDITIONS, Collection.owner_id == user.id)

    content_rows = session.exec(
        select(EntityContent, Entity)
        .join(Entity, EntityContent.entity_id == Entity.id)
        .join(Collection, EntityContent.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*content_conditions)
        .order_by(EntityContent.confirmed_at.desc()),
    ).all()

    image_rows = session.exec(
        select(ImageRecord, ImageGeneration, Entity)
        .join(ImageGeneration, ImageRecord.generation_id == ImageGeneration.id)
        .join(Entity, ImageRecord.entity_id == Entity.id)
        .join(Collection, ImageRecord.collection_id == Collection.id)
        .join(User, Collection.owner_id == User.id)
        .where(*image_conditions)
        .order_by(ImageRecord.created_at.desc()),
    ).all()

    return PublicProfileResponse(
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=get_avatar_info(user)["avatar_url"],
        shared_contents=[
            SharedContentSummary(
                id=ec.id,
                content=ec.content,
                category=ec.category,
                entity_name=en.name,
                entity_type=en.type,
                confirmed_at=ec.confirmed_at,
                created_at=ec.created_at,
            )
            for ec, en in content_rows
        ],
        shared_images=[
            SharedImageSummary(
                id=img.id,
                generation_id=img.generation_id,
                image_url=img.image_url or build_storage_url(img.storage_path),
                storage_path=img.storage_path,
                seed=img.seed,
                auto_prompt=gen.auto_prompt,
                final_prompt=gen.final_prompt,
                entity_name=en.name,
                entity_type=en.type,
                created_at=img.created_at,
            )
            for img, gen, en in image_rows
        ],
    )


async def upload_profile_image(session: Session, user: User, file: UploadFile) -> str:
    """Sube o reemplaza la imagen de perfil de un usuario."""
    if not re.match(r"^[A-Za-z0-9_-]{3,50}$", user.username):
        msg = f"Username inválido para construcción de ruta: {user.username!r}"
        raise ValueError(
            msg,
        )

    max_bytes = int(settings.profile_image_max_size_mb * 1024 * 1024)
    content = FileValidator.validate_image(file, max_bytes=max_bytes)

    ext = Path(file.filename or "image.jpg").suffix.lower()
    unique_filename = generate_unique_filename(ext)
    relative_path = f"users/{user.username}/img/profile/{unique_filename}"

    if settings.storage_backend == "s3":
        if user.avatar_path:
            from app.core.storage.s3_client import get_s3_client

            get_s3_client().delete_object(Bucket=settings.s3_bucket, Key=user.avatar_path)
    else:
        profile_dir = _get_profile_dir(user.username)
        profile_dir.mkdir(parents=True, exist_ok=True)
        for existing in profile_dir.iterdir():
            if existing.is_file():
                existing.unlink()

    save_file(content, relative_path)

    user.avatar_path = relative_path
    session.add(user)
    db_commit(session, f"upload_profile_image({user.username})")

    return build_storage_url(relative_path)


def delete_profile_image(session: Session, user: User) -> None:
    """Elimina la imagen de perfil de un usuario."""
    if not user.avatar_path:
        return

    if settings.storage_backend == "s3":
        delete_file(user.avatar_path)
    else:
        profile_dir = _get_profile_dir(user.username)
        if profile_dir.exists() and profile_dir.is_dir():
            media_root_resolved = Path(settings.media_root).resolve()
            for item in profile_dir.iterdir():
                resolved = item.resolve()
                if resolved.is_file() and resolved.is_relative_to(media_root_resolved):
                    resolved.unlink()
                elif resolved.is_dir() and resolved.is_relative_to(media_root_resolved):
                    shutil.rmtree(resolved)
            with contextlib.suppress(OSError):
                profile_dir.rmdir()

    user.avatar_path = None
    session.add(user)
    db_commit(session, f"delete_profile_image({user.username})")
