from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import current_user, password_hash
from ..database import get_db
from ..models import Pet, PetOwner, User
from ..schemas import LoginRequest, RegisterRequest, UserRead


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    first_account = db.scalar(select(User.id).limit(1)) is None
    user = User(email=email, password_hash=password_hash.hash(payload.password))
    db.add(user)
    try:
        db.flush()
        if first_account:
            unowned_pets = db.scalars(
                select(Pet.id).outerjoin(PetOwner, PetOwner.pet_id == Pet.id)
                .where(PetOwner.pet_id.is_(None))
            ).all()
            db.add_all(PetOwner(pet_id=pet_id, user_id=user.id) for pet_id in unowned_pets)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    db.refresh(user)
    request.session["user_id"] = user.id
    return user


@router.post("/login", response_model=UserRead)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not password_hash.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    request.session["user_id"] = user.id
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request):
    request.session.clear()


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(current_user)):
    return user
