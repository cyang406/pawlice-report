from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Incident, PetOwner, User
from ..storage import remove_image


router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def find_incident(db: Session, incident_id: int, user_id: int) -> Incident:
    incident = db.get(Incident, incident_id)
    owner = db.scalar(
        select(PetOwner).where(PetOwner.pet_id == incident.pet_id, PetOwner.user_id == user_id)
    ) if incident is not None else None
    if owner is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    incident = find_incident(db, incident_id, user.id)
    db.delete(incident)
    db.commit()
    remove_image("incidents", incident_id)
