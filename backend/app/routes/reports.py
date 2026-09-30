from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import User
from ..reports.calculator import calculate_report
from ..reports.report_writer import generate_narrative
from ..schemas import ReportRequest, ReportResponse
from .pets import find_pet


router = APIRouter(prefix="/api/pets", tags=["reports"])


@router.post("/{pet_id}/reports", response_model=ReportResponse)
def create_report(pet_id: int, payload: ReportRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    pet = find_pet(db, pet_id, user.id)
    start, end, stats, notable = calculate_report(db, pet_id, payload.period)
    narrative, source = generate_narrative(pet, payload.period, stats, notable)
    return ReportResponse(
        pet_id=pet.id,
        pet_name=pet.name,
        period=payload.period,
        period_start=start,
        period_end=end,
        stats=stats,
        notable_events=notable,
        **narrative.model_dump(),
        narrative_source=source,
    )
