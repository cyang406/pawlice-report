from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, utc_now


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    species: Mapped[str] = mapped_column(String(100))
    breed: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    incidents: Mapped[list["Incident"]] = relationship(back_populates="pet")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PetOwner(Base):
    """Ownership lives in a new table so existing pet rows need no ALTER TABLE."""

    __tablename__ = "pet_owners"

    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (CheckConstraint("severity BETWEEN 1 AND 5", name="ck_incidents_severity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, default="INCIDENT", server_default="INCIDENT")
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    incident_time: Mapped[datetime] = mapped_column(DateTime)
    image_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    pet: Mapped[Pet] = relationship(back_populates="incidents")
