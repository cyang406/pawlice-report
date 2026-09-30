from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db, utc_now
from ..models import Incident, Pet, PetOwner, User
from ..schemas import EventCreate, EventRead, EventType, IncidentCreate, IncidentRead, PetCreate, PetRead, PetStats
from ..storage import remove_image


router = APIRouter(prefix="/api/pets", tags=["pets"])


def find_pet(db: Session, pet_id: int, user_id: int) -> Pet:
    pet = db.scalar(
        select(Pet).join(PetOwner, PetOwner.pet_id == Pet.id)
        .where(Pet.id == pet_id, PetOwner.user_id == user_id)
    )
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


@router.post("", response_model=PetRead, status_code=status.HTTP_201_CREATED)
def create_pet(payload: PetCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    pet = Pet(**payload.model_dump())
    db.add(pet)
    db.flush()
    db.add(PetOwner(pet_id=pet.id, user_id=user.id))
    db.commit()
    db.refresh(pet)
    return pet


@router.get("", response_model=list[PetRead])
def list_pets(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.scalars(
        select(Pet).join(PetOwner, PetOwner.pet_id == Pet.id)
        .where(PetOwner.user_id == user.id)
        .order_by(Pet.created_at.desc(), Pet.id.desc())
    ).all()


@router.get("/{pet_id}", response_model=PetRead)
def get_pet(pet_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return find_pet(db, pet_id, user.id)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(pet_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    pet = find_pet(db, pet_id, user.id)
    incident_ids = db.scalars(select(Incident.id).where(Incident.pet_id == pet_id)).all()
    db.execute(delete(Incident).where(Incident.pet_id == pet_id))
    db.execute(delete(PetOwner).where(PetOwner.pet_id == pet_id))
    db.delete(pet)
    db.commit()
    remove_image("pets", pet_id)
    for incident_id in incident_ids:
        remove_image("incidents", incident_id)


@router.post("/{pet_id}/incidents", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(pet_id: int, payload: IncidentCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    find_pet(db, pet_id, user.id)
    incident = Incident(pet_id=pet_id, event_type=EventType.INCIDENT.value, **payload.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.get("/{pet_id}/incidents", response_model=list[IncidentRead])
def list_incidents(pet_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    find_pet(db, pet_id, user.id)
    return db.scalars(
        select(Incident)
        .where(Incident.pet_id == pet_id, Incident.event_type == EventType.INCIDENT.value)
        .order_by(Incident.incident_time.desc(), Incident.id.desc())
    ).all()


@router.post("/{pet_id}/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(pet_id: int, payload: EventCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    find_pet(db, pet_id, user.id)
    event = Incident(
        pet_id=pet_id,
        event_type=payload.event_type.value,
        category=payload.category,
        description=payload.description,
        severity=payload.severity,
        incident_time=payload.event_time,
        image_url=payload.image_url,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{pet_id}/events", response_model=list[EventRead])
def list_events(pet_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    find_pet(db, pet_id, user.id)
    return db.scalars(
        select(Incident)
        .where(Incident.pet_id == pet_id)
        .order_by(Incident.incident_time.desc(), Incident.id.desc())
    ).all()


@router.get("/{pet_id}/stats", response_model=PetStats)
def get_pet_stats(pet_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    find_pet(db, pet_id, user.id)
    events = db.scalars(select(Incident).where(Incident.pet_id == pet_id)).all()
    event_counts = Counter(event.event_type for event in events)
    incidents = [event for event in events if event.event_type == EventType.INCIDENT.value]

    now = utc_now()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    next_week_start = week_start + timedelta(days=7)
    counts = Counter(incident.category for incident in incidents)
    most_common = sorted(counts, key=lambda category: (-counts[category], category))[0] if counts else None
    severities = [incident.severity for incident in incidents if incident.severity is not None]

    return PetStats(
        total_incidents=len(incidents),
        incidents_this_week=sum(week_start <= i.incident_time < next_week_start for i in incidents),
        most_common_category=most_common,
        average_severity=round(sum(severities) / len(severities), 2) if severities else None,
        total_events=len(events),
        incident_count=event_counts[EventType.INCIDENT.value],
        good_conduct_count=event_counts[EventType.GOOD_CONDUCT.value],
        funny_moment_count=event_counts[EventType.FUNNY_MOMENT.value],
        wellness_count=event_counts[EventType.WELLNESS.value],
    )
