from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Incident, PetOwner, User
from ..storage import remove_image


router = APIRouter(prefix="/api/events", tags=["events"])


def find_event(db: Session, event_id: int, user_id: int) -> Incident:
    event = db.scalar(
        select(Incident).join(PetOwner, PetOwner.pet_id == Incident.pet_id)
        .where(Incident.id == event_id, PetOwner.user_id == user_id)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = find_event(db, event_id, user.id)
    db.delete(event)
    db.commit()
    remove_image("incidents", event_id)
