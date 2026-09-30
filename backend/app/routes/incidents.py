from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Incident, User
from ..schemas import EventType
from ..storage import remove_image
from .events import find_event


router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def find_incident(db: Session, incident_id: int, user_id: int) -> Incident:
    try:
        incident = find_event(db, incident_id, user_id)
    except HTTPException as exc:
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    if incident.event_type != EventType.INCIDENT.value:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    incident = find_incident(db, incident_id, user.id)
    db.delete(incident)
    db.commit()
    remove_image("incidents", incident_id)
