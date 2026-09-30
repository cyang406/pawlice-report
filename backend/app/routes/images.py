from secrets import token_hex

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import User
from ..schemas import IncidentRead, PetRead
from ..storage import image_path, prepare_image, save_image
from .incidents import find_incident
from .pets import find_pet


router = APIRouter(tags=["images"])


@router.post("/api/images/prepare", response_class=Response)
def prepare_mugshot_image(file: UploadFile = File(...), user: User = Depends(current_user)):
    return Response(
        content=prepare_image(file),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


def image_response(kind: str, record_id: int) -> FileResponse:
    path = image_path(kind, record_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/api/pets/{pet_id}/image", response_model=PetRead)
def upload_pet_image(
    pet_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    pet = find_pet(db, pet_id, user.id)
    save_image(file, "pets", pet_id)
    pet.image_url = f"/api/pets/{pet_id}/image?v={token_hex(8)}"
    db.commit()
    db.refresh(pet)
    return pet


@router.get("/api/pets/{pet_id}/image", response_class=FileResponse)
def get_pet_image(pet_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    pet = find_pet(db, pet_id, user.id)
    if not pet.image_url or not pet.image_url.startswith(f"/api/pets/{pet_id}/image?"):
        raise HTTPException(status_code=404, detail="Image not found")
    return image_response("pets", pet_id)


@router.post("/api/incidents/{incident_id}/image", response_model=IncidentRead)
def upload_incident_image(
    incident_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    incident = find_incident(db, incident_id, user.id)
    save_image(file, "incidents", incident_id)
    incident.image_url = f"/api/incidents/{incident_id}/image?v={token_hex(8)}"
    db.commit()
    db.refresh(incident)
    return incident


@router.get("/api/incidents/{incident_id}/image", response_class=FileResponse)
def get_incident_image(incident_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    incident = find_incident(db, incident_id, user.id)
    if not incident.image_url or not incident.image_url.startswith(f"/api/incidents/{incident_id}/image?"):
        raise HTTPException(status_code=404, detail="Image not found")
    return image_response("incidents", incident_id)
