from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator, model_validator

from .database import utc_now


class Category(str, Enum):
    FOOD_THEFT = "Food Theft"
    PROPERTY_DAMAGE = "Property Damage"
    SIBLING_ASSAULT = "Sibling Assault"
    ZOOMIES = "3AM Zoomies"
    UNAUTHORIZED_ENTRY = "Unauthorized Entry"
    PLANT_DESTRUCTION = "Plant Destruction"
    PUBLIC_DISTURBANCE = "Public Disturbance"
    FURNITURE_DAMAGE = "Furniture Damage"
    SUSPICIOUS_ACTIVITY = "Suspicious Activity"
    OTHER = "Other"


class EventType(str, Enum):
    INCIDENT = "INCIDENT"
    GOOD_CONDUCT = "GOOD_CONDUCT"
    FUNNY_MOMENT = "FUNNY_MOMENT"
    WELLNESS = "WELLNESS"


EVENT_CATEGORIES = {
    EventType.INCIDENT: {category.value for category in Category},
    EventType.GOOD_CONDUCT: {"Good Behavior", "Learned Something New", "Calm During Grooming", "Friendly Interaction", "Other"},
    EventType.FUNNY_MOMENT: {"Weird Sleeping Position", "Funny Reaction", "Got Stuck Somewhere", "Random Chaos", "Other"},
    EventType.WELLNESS: {"Weight Check", "Teeth Brushing", "Nail Trim", "Bath", "Grooming", "Other"},
}


def normalize_utc_datetime(value: datetime) -> datetime:
    # Treat datetimes without an offset as UTC; store all values as UTC.
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class PetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    species: str = Field(min_length=1, max_length=100)
    breed: Optional[str] = Field(default=None, max_length=100)
    birthday: Optional[date] = None
    image_url: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("name", "species")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be blank")
        return value


class PetRead(PetCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class IncidentCreate(BaseModel):
    category: Category
    description: str = Field(min_length=1)
    severity: int = Field(ge=1, le=5)
    incident_time: datetime = Field(default_factory=utc_now)

    @field_validator("description")
    @classmethod
    def nonblank_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be blank")
        return value

    @field_validator("incident_time")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)


class IncidentRead(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    image_url: Optional[str] = None
    created_at: datetime

    @field_serializer("incident_time", "created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class EventCreate(BaseModel):
    event_type: EventType
    category: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1)
    severity: Optional[int] = None
    event_time: datetime = Field(default_factory=utc_now)
    image_url: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("description")
    @classmethod
    def nonblank_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be blank")
        return value

    @field_validator("event_time")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def validate_type_fields(self):
        if self.category not in EVENT_CATEGORIES[self.event_type]:
            raise ValueError("Category is not valid for this event type")
        if self.event_type == EventType.INCIDENT:
            if self.severity is None or not 1 <= self.severity <= 5:
                raise ValueError("Incidents require severity from 1 to 5")
        else:
            self.severity = None
        return self


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    event_type: EventType
    category: str
    description: str
    severity: Optional[int]
    event_time: datetime = Field(validation_alias="incident_time")
    image_url: Optional[str]
    created_at: datetime

    @field_serializer("event_time", "created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class PetStats(BaseModel):
    total_incidents: int
    incidents_this_week: int
    most_common_category: Optional[Category]
    average_severity: Optional[float]
    total_events: int
    incident_count: int
    good_conduct_count: int
    funny_moment_count: int
    wellness_count: int


class ReportRequest(BaseModel):
    period: str

    @field_validator("period")
    @classmethod
    def valid_period(cls, value: str) -> str:
        if value not in {"weekly", "monthly"}:
            raise ValueError("Period must be weekly or monthly")
        return value


class ReportStats(BaseModel):
    total_events: int
    incident_count: int
    good_conduct_count: int
    funny_moment_count: int
    wellness_count: int
    most_common_incident_category: Optional[str]
    average_incident_severity: Optional[float]
    most_active_event_day: Optional[str]


class ReportResponse(BaseModel):
    pet_id: int
    pet_name: str
    period: str
    period_start: datetime
    period_end: datetime
    stats: ReportStats
    notable_events: list[EventRead]
    headline: str
    officer_summary: str
    verdict: str
    sentence: str
    narrative_source: str

    @field_serializer("period_start", "period_end")
    def serialize_period_time(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
