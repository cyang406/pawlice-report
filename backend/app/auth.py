from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from .database import get_db
from .models import User


password_hash = PasswordHash.recommended()


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if isinstance(user_id, int) else None
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in")
    return user
