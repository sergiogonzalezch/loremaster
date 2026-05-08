from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.core.auth import create_access_token, hash_password, verify_password
from app.database import get_session
from app.models.users import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == request.username)
    user = session.exec(statement).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    token = create_access_token(
        data={"sub": user.id, "username": user.username, "is_admin": user.is_admin}
    )
    return {"access_token": token}


@router.post("/register", response_model=TokenResponse)
def register(request: LoginRequest, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == request.username)
    if session.exec(statement).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        )

    new_user = User(
        username=request.username, hashed_password=hash_password(request.password)
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    token = create_access_token(
        data={"sub": new_user.id, "username": new_user.username, "is_admin": False}
    )
    return {"access_token": token}
