from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session, select
from app.core.auth import create_access_token, hash_password, verify_password
from app.core.auth.dependencies import get_current_user
from app.database import get_session
from app.models.db.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, session: Session = Depends(get_session)):
    statement = select(User).where(
        (User.username == request.username_or_email)
        | (User.email == request.username_or_email),
        User.is_deleted == False,
    )
    user = session.exec(statement).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    token = create_access_token(
        data={
            "sub": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "version": user.token_version,
        }
    )
    return {"access_token": token}


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, session: Session = Depends(get_session)):
    existing_username = session.exec(
        select(User).where(User.username == request.username)
    ).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        )

    existing_email = session.exec(
        select(User).where(User.email == request.email, User.is_deleted == False)
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado",
        )

    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    token = create_access_token(
        data={
            "sub": new_user.id,
            "username": new_user.username,
            "is_admin": False,
            "version": new_user.token_version,
        }
    )
    return {"access_token": token}


@router.post("/logout", status_code=204)
def logout(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    user = session.get(User, current_user["sub"])
    if user and not user.is_deleted:
        user.token_version += 1
        session.add(user)
        session.commit()
