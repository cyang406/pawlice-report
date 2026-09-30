from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator

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
    image_url: Optional[str] = Field(default=None, max_length=2048)

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
        # Treat datetimes without an offset as UTC; store all values as UTC.
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


class IncidentRead(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    created_at: datetime

    @field_serializer("incident_time", "created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class PetStats(BaseModel):
    total_incidents: int
    incidents_this_week: int
    most_common_category: Optional[Category]
    average_severity: Optional[float]


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
