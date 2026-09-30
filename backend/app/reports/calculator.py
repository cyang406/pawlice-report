"""Deterministic report facts from stored journal events."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import utc_now
from ..models import Incident
from ..schemas import EventType, ReportStats


def period_bounds(period: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return an inclusive UTC start and exclusive UTC end (naive for MySQL DATETIME)."""
    now = now or utc_now()
    if period == "weekly":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=7)
    if period == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
        return start, end
    raise ValueError("Period must be weekly or monthly")


def select_notable_events(events: list[Incident]) -> list[Incident]:
    """Take one per type (highest severity incident), then fill to five by recency."""
    newest = sorted(events, key=lambda event: (event.incident_time, event.id), reverse=True)
    selected = []
    for event_type in EventType:
        candidates = [event for event in newest if event.event_type == event_type.value]
        if candidates:
            chosen = (max(candidates, key=lambda event: (event.severity or 0, event.incident_time, event.id))
                      if event_type == EventType.INCIDENT else candidates[0])
            selected.append(chosen)
    selected_ids = {event.id for event in selected}
    for event in newest:
        if len(selected) >= 5:
            break
        if event.id not in selected_ids:
            selected.append(event)
            selected_ids.add(event.id)
    return sorted(selected, key=lambda event: (event.incident_time, event.id), reverse=True)


def calculate_report(db: Session, pet_id: int, period: str, now: datetime | None = None):
    start, end = period_bounds(period, now)
    events = db.scalars(
        select(Incident).where(
            Incident.pet_id == pet_id,
            Incident.incident_time >= start,
            Incident.incident_time < end,
        )
    ).all()
    counts = Counter(event.event_type for event in events)
    incidents = [event for event in events if event.event_type == EventType.INCIDENT.value]
    categories = Counter(event.category for event in incidents)
    top_category = min(categories, key=lambda category: (-categories[category], category)) if categories else None
    severities = [event.severity for event in incidents if event.severity is not None]
    days = Counter(event.incident_time.date() for event in events)
    # For equal activity, the earliest UTC calendar date wins.
    busiest_date = min(days, key=lambda day: (-days[day], day)) if days else None
    stats = ReportStats(
        total_events=len(events),
        incident_count=counts[EventType.INCIDENT.value],
        good_conduct_count=counts[EventType.GOOD_CONDUCT.value],
        funny_moment_count=counts[EventType.FUNNY_MOMENT.value],
        wellness_count=counts[EventType.WELLNESS.value],
        most_common_incident_category=top_category,
        average_incident_severity=round(sum(severities) / len(severities), 2) if severities else None,
        most_active_event_day=busiest_date.strftime("%A") if busiest_date else None,
    )
    return start, end, stats, select_notable_events(events)
