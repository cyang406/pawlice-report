import os
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SESSION_SECRET", "test-session-secret-longer-than-thirty-two-characters")

from app.database import Base
from app.models import Incident, Pet
from app.reports.calculator import calculate_report, period_bounds, select_notable_events
from app.reports.report_writer import Narrative, write_with_openai
from app.schemas import ReportStats


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_event(db, pet_id, event_type, category, when, severity=None, description="Record"):
    event = Incident(pet_id=pet_id, event_type=event_type, category=category,
                     description=description, severity=severity, incident_time=when)
    db.add(event)
    db.flush()
    return event


def test_period_bounds():
    assert period_bounds("weekly", datetime(2026, 1, 1, 17, 30)) == (
        datetime(2025, 12, 29), datetime(2026, 1, 5))
    assert period_bounds("weekly", datetime(2026, 1, 5)) == (
        datetime(2026, 1, 5), datetime(2026, 1, 12))
    assert period_bounds("monthly", datetime(2024, 2, 29, 23, 59)) == (
        datetime(2024, 2, 1), datetime(2024, 3, 1))
    assert period_bounds("monthly", datetime(2026, 12, 31)) == (
        datetime(2026, 12, 1), datetime(2027, 1, 1))
    with pytest.raises(ValueError):
        period_bounds("yearly", datetime(2026, 1, 1))


def test_empty_period_and_no_incidents(db):
    pet = Pet(name="Mochi", species="Cat")
    db.add(pet)
    db.flush()
    _, _, empty, notable = calculate_report(db, pet.id, "monthly", datetime(2026, 9, 10))
    assert empty.total_events == 0
    assert empty.most_common_incident_category is None
    assert empty.average_incident_severity is None
    assert empty.most_active_event_day is None
    assert notable == []

    add_event(db, pet.id, "GOOD_CONDUCT", "Good Behavior", datetime(2026, 9, 8))
    _, _, stats, notable = calculate_report(db, pet.id, "monthly", datetime(2026, 9, 10))
    assert stats.total_events == 1
    assert stats.good_conduct_count == 1
    assert stats.incident_count == 0
    assert stats.most_common_incident_category is None
    assert stats.average_incident_severity is None
    assert len(notable) == 1


def test_facts_boundaries_ties_and_notables(db):
    pet = Pet(name="Pip", species="Dog")
    db.add(pet)
    db.flush()
    # The selected week is 2026-09-28 through 2026-10-05, end exclusive.
    add_event(db, pet.id, "INCIDENT", "Other", datetime(2026, 9, 27, 23, 59), 5)
    first = add_event(db, pet.id, "INCIDENT", "Food Theft", datetime(2026, 9, 28), 2)
    high = add_event(db, pet.id, "INCIDENT", "Other", datetime(2026, 9, 28, 12), 5)
    funny = add_event(db, pet.id, "FUNNY_MOMENT", "Funny Reaction", datetime(2026, 9, 28, 13))
    good = add_event(db, pet.id, "GOOD_CONDUCT", "Good Behavior", datetime(2026, 9, 29, 8), 5)
    wellness = add_event(db, pet.id, "WELLNESS", "Bath", datetime(2026, 9, 29, 9))
    add_event(db, pet.id, "INCIDENT", "Food Theft", datetime(2026, 10, 5), 1)

    start, end, stats, notable = calculate_report(db, pet.id, "weekly", datetime(2026, 9, 30))
    assert (start, end) == (datetime(2026, 9, 28), datetime(2026, 10, 5))
    assert stats.model_dump() == {
        "total_events": 5, "incident_count": 2, "good_conduct_count": 1,
        "funny_moment_count": 1, "wellness_count": 1,
        "most_common_incident_category": "Food Theft",  # tied categories: alphabetical
        "average_incident_severity": 3.5,
        "most_active_event_day": "Monday",  # tied dates: earliest date
    }
    assert [event.id for event in notable] == [wellness.id, good.id, funny.id, high.id, first.id]


def test_notable_selection_prefers_high_severity_and_limits_five(db):
    pet = Pet(name="Nori", species="Cat")
    db.add(pet)
    db.flush()
    low = add_event(db, pet.id, "INCIDENT", "Other", datetime(2026, 9, 30, 12), 1)
    high = add_event(db, pet.id, "INCIDENT", "Other", datetime(2026, 9, 28), 5)
    for day in range(25, 30):
        add_event(db, pet.id, "FUNNY_MOMENT", "Funny Reaction", datetime(2026, 9, day))
    add_event(db, pet.id, "GOOD_CONDUCT", "Good Behavior", datetime(2026, 9, 27))
    add_event(db, pet.id, "WELLNESS", "Bath", datetime(2026, 9, 26))
    selected = select_notable_events(db.query(Incident).filter_by(pet_id=pet.id).all())
    assert len(selected) == 5
    assert high.id in {event.id for event in selected}
    assert low.id in {event.id for event in selected}  # one recent fill slot
    assert {event.event_type for event in selected} == {"INCIDENT", "FUNNY_MOMENT", "GOOD_CONDUCT", "WELLNESS"}
    assert selected == sorted(selected, key=lambda event: (event.incident_time, event.id), reverse=True)


def test_openai_writer_sends_only_selected_facts_and_validates_output(db, monkeypatch):
    import json
    from types import SimpleNamespace
    import openai

    pet = Pet(name="Nori", species="Cat")
    db.add(pet)
    db.flush()
    event = add_event(db, pet.id, "INCIDENT", "Food Theft", datetime(2026, 9, 30), 3, "Took a biscuit")
    stats = ReportStats(total_events=1, incident_count=1, good_conduct_count=0,
                        funny_moment_count=0, wellness_count=0,
                        most_common_incident_category="Food Theft",
                        average_incident_severity=3.0, most_active_event_day="Wednesday")
    captured = {}

    def parse(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_parsed={
            "headline": "Case Closed", "officer_summary": "Nori took a biscuit.",
            "verdict": "Very cute.", "sentence": "Extra cuddles.",
        })

    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    narrative = write_with_openai("test-key", pet, "weekly", stats, [event])
    assert isinstance(narrative, Narrative)
    assert captured["text_format"] is Narrative
    assert set(json.loads(captured["input"])) == {"pet_name", "period", "statistics", "notable_events"}
    assert json.loads(captured["input"])["notable_events"][0]["description"] == "Took a biscuit"
