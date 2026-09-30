import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SESSION_SECRET", "test-session-secret-longer-than-thirty-two-characters")

from app import main
from app.database import Base, get_db
from app.models import Incident, Pet, PetOwner, User
from app import storage
from app.reports import calculator, report_writer


def register(client, email="owner@example.com"):
    response = client.post("/api/auth/register", json={"email": email, "password": "safe-password-123"})
    assert response.status_code == 201
    return response


@pytest.fixture
def client(monkeypatch, tmp_path):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(storage, "upload_dir", tmp_path / "uploads")
    sessions = sessionmaker(bind=engine)

    def test_db():
        with sessions() as session:
            yield session

    main.app.dependency_overrides[get_db] = test_db
    monkeypatch.setattr(main, "engine", engine)
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    engine.dispose()


def test_pet_incident_and_stats_flow(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/pets").status_code == 401
    register(client)
    assert client.get("/api/pets").json() == []

    created = client.post(
        "/api/pets",
        json={
            "name": "  Mochi  ",
            "species": "Cat",
            "breed": "Tabby",
            "birthday": "2022-04-01",
            "image_url": "https://example.com/mochi.jpg",
        },
    )
    assert created.status_code == 201
    pet = created.json()
    pet_id = pet["id"]
    assert pet["name"] == "Mochi"
    assert pet["image_url"] == "https://example.com/mochi.jpg"
    assert pet["created_at"].endswith("Z")
    assert client.get(f"/api/pets/{pet_id}").json() == pet
    assert client.get("/api/pets").json() == [pet]
    assert client.get(f"/api/pets/{pet_id}/stats").json() == {
        "total_incidents": 0,
        "incidents_this_week": 0,
        "most_common_category": None,
        "average_severity": None,
        "total_events": 0,
        "incident_count": 0,
        "good_conduct_count": 0,
        "funny_moment_count": 0,
        "wellness_count": 0,
    }

    now = datetime.now(timezone.utc)
    previous_week = now - timedelta(days=now.weekday() + 1)
    incidents = [
        ("Food Theft", 2, now),
        ("Food Theft", 4, now),
        ("Plant Destruction", 3, previous_week),
    ]
    ids = []
    for category, severity, incident_time in incidents:
        response = client.post(
            f"/api/pets/{pet_id}/incidents",
            json={
                "category": category,
                "description": "Caught red-pawed",
                "severity": severity,
                "incident_time": incident_time.isoformat(),
            },
        )
        assert response.status_code == 201
        assert response.json()["image_url"] is None
        assert response.json()["incident_time"].endswith("Z")
        ids.append(response.json()["id"])

    listed = client.get(f"/api/pets/{pet_id}/incidents").json()
    assert len(listed) == 3
    assert listed[-1]["id"] == ids[-1]
    assert client.get(f"/api/pets/{pet_id}/stats").json() == {
        "total_incidents": 3,
        "incidents_this_week": 2,
        "most_common_category": "Food Theft",
        "average_severity": 3.0,
        "total_events": 3,
        "incident_count": 3,
        "good_conduct_count": 0,
        "funny_moment_count": 0,
        "wellness_count": 0,
    }

    assert client.delete(f"/api/incidents/{ids[0]}").status_code == 204
    assert len(client.get(f"/api/pets/{pet_id}/incidents").json()) == 2
    assert client.get(f"/api/pets/{pet_id}/stats").json()["total_incidents"] == 2
    assert client.delete(f"/api/incidents/{ids[0]}").status_code == 404


def test_validation_and_missing_records(client):
    register(client)
    assert client.post("/api/pets", json={"name": "  ", "species": "Cat"}).status_code == 422
    assert client.get("/api/pets/999").status_code == 404
    assert client.get("/api/pets/999/incidents").status_code == 404
    assert client.get("/api/pets/999/stats").status_code == 404

    pet_id = client.post("/api/pets", json={"name": "Pip", "species": "Dog"}).json()["id"]
    for category, description, severity in [
        ("Unknown Crime", "Bad behavior", 2),
        ("Food Theft", "   ", 2),
        ("Food Theft", "Bad behavior", None),
        ("Food Theft", "Bad behavior", 6),
    ]:
        response = client.post(
            f"/api/pets/{pet_id}/incidents",
            json={"category": category, "description": description, "severity": severity},
        )
        assert response.status_code == 422
    assert client.post(
        "/api/pets/999/incidents",
        json={"category": "Food Theft", "description": "Bad behavior", "severity": 2},
    ).status_code == 404


def test_events_keep_incident_routes_isolated_and_stats_correct(client):
    register(client)
    pet_id = client.post("/api/pets", json={"name": "Mochi", "species": "Cat"}).json()["id"]
    legacy = client.post(
        f"/api/pets/{pet_id}/incidents",
        json={"category": "Food Theft", "description": "Stole lunch", "severity": 2,
              "incident_time": "2025-01-01T12:00:00Z", "event_type": "GOOD_CONDUCT"},
    )
    assert legacy.status_code == 201
    legacy_id = legacy.json()["id"]

    entries = [
        ("GOOD_CONDUCT", "Good Behavior", "2025-01-02T12:00:00Z", {}),
        ("FUNNY_MOMENT", "Weird Sleeping Position", "2025-01-03T12:00:00Z", {"severity": None}),
        ("WELLNESS", "Grooming", "2025-01-04T12:00:00Z", {"severity": 5}),
        ("INCIDENT", "Property Damage", "2025-01-05T12:00:00Z", {"severity": 4}),
    ]
    created = []
    for event_type, category, event_time, extra in entries:
        response = client.post(
            f"/api/pets/{pet_id}/events",
            json={"event_type": event_type, "category": category, "description": "Case note",
                  "event_time": event_time, **extra},
        )
        assert response.status_code == 201, response.text
        assert response.json()["event_type"] == event_type
        assert response.json()["event_time"] == event_time
        created.append(response.json())

    assert created[0]["severity"] is None
    assert created[1]["severity"] is None
    assert created[2]["severity"] is None
    assert [event["id"] for event in client.get(f"/api/pets/{pet_id}/events").json()] == [
        created[3]["id"], created[2]["id"], created[1]["id"], created[0]["id"], legacy_id,
    ]
    assert [incident["id"] for incident in client.get(f"/api/pets/{pet_id}/incidents").json()] == [
        created[3]["id"], legacy_id,
    ]
    assert client.get(f"/api/pets/{pet_id}/stats").json() == {
        "total_incidents": 2, "incidents_this_week": 0,
        "most_common_category": "Food Theft", "average_severity": 3.0,
        "total_events": 5, "incident_count": 2, "good_conduct_count": 1,
        "funny_moment_count": 1, "wellness_count": 1,
    }

    funny_id = created[1]["id"]
    assert client.delete(f"/api/incidents/{funny_id}").status_code == 404
    assert client.post(
        f"/api/incidents/{funny_id}/image",
        files={"file": ("evidence.png", png_bytes(), "image/png")},
    ).status_code == 404
    uploaded = client.post(
        f"/api/events/{funny_id}/image",
        files={"file": ("evidence.png", png_bytes(), "image/png")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["image_url"].startswith(f"/api/events/{funny_id}/image?")
    assert client.get(uploaded.json()["image_url"]).status_code == 200
    assert storage.image_path("incidents", funny_id).is_file()
    incident_image = client.post(
        f"/api/events/{created[3]['id']}/image",
        files={"file": ("evidence.png", png_bytes(), "image/png")},
    )
    assert incident_image.status_code == 200
    assert client.get(f"/api/incidents/{created[3]['id']}/image").status_code == 200

    assert client.post("/api/auth/logout").status_code == 204
    register(client, "other@example.com")
    assert client.get(f"/api/pets/{pet_id}/events").status_code == 404
    assert client.delete(f"/api/events/{funny_id}").status_code == 404
    assert client.get(uploaded.json()["image_url"]).status_code == 404
    assert client.post(
        f"/api/pets/{pet_id}/events",
        json={"event_type": "WELLNESS", "category": "Bath", "description": "Clean"},
    ).status_code == 404
    assert client.post("/api/auth/logout").status_code == 204
    assert client.post("/api/auth/login", json={"email": "owner@example.com", "password": "safe-password-123"}).status_code == 200

    assert client.delete(f"/api/events/{funny_id}").status_code == 204
    assert not storage.image_path("incidents", funny_id).exists()
    assert client.get(f"/api/pets/{pet_id}/stats").json()["total_events"] == 4
    assert len(client.get(f"/api/pets/{pet_id}/incidents").json()) == 2


def test_event_validation(client):
    register(client)
    pet_id = client.post("/api/pets", json={"name": "Pip", "species": "Dog"}).json()["id"]
    incident = {"event_type": "INCIDENT", "category": "Food Theft", "description": "Stole a treat"}
    for severity in (None, 0, 6):
        response = client.post(f"/api/pets/{pet_id}/events", json={**incident, "severity": severity})
        assert response.status_code == 422
    for event_type, category in [
        ("INCIDENT", "Good Behavior"),
        ("GOOD_CONDUCT", "Food Theft"),
        ("FUNNY_MOMENT", "Bath"),
        ("WELLNESS", "Random Chaos"),
        ("UNKNOWN", "Other"),
    ]:
        assert client.post(
            f"/api/pets/{pet_id}/events",
            json={"event_type": event_type, "category": category, "description": "Case note", "severity": 3},
        ).status_code == 422
    assert client.get("/api/pets/999/events").status_code == 404
    assert client.post(
        "/api/pets/999/events",
        json={"event_type": "GOOD_CONDUCT", "category": "Good Behavior", "description": "Sat nicely"},
    ).status_code == 404
    assert client.get(f"/api/pets/{pet_id}/events").json() == []


def test_accounts_isolate_pets_and_delete_profile_with_incidents(client):
    registration = register(client)
    assert "httponly" in registration.headers["set-cookie"].lower()
    assert "samesite=lax" in registration.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").json()["email"] == "owner@example.com"
    assert client.post("/api/auth/register", json={"email": "OWNER@example.com", "password": "another-password"}).status_code == 409

    pet_id = client.post("/api/pets", json={"name": "Pip", "species": "Dog"}).json()["id"]
    incident_id = client.post(
        f"/api/pets/{pet_id}/incidents",
        json={"category": "Food Theft", "description": "Stole lunch", "severity": 3},
    ).json()["id"]

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/pets").status_code == 401
    assert client.post("/api/auth/login", json={"email": "owner@example.com", "password": "wrong"}).status_code == 401

    register(client, "other@example.com")
    assert client.get("/api/pets").json() == []
    assert client.get(f"/api/pets/{pet_id}").status_code == 404
    assert client.get(f"/api/pets/{pet_id}/incidents").status_code == 404
    assert client.get(f"/api/pets/{pet_id}/stats").status_code == 404
    assert client.post(
        f"/api/pets/{pet_id}/incidents",
        json={"category": "Other", "description": "Trespass", "severity": 1},
    ).status_code == 404
    assert client.delete(f"/api/incidents/{incident_id}").status_code == 404
    assert client.delete(f"/api/pets/{pet_id}").status_code == 404

    assert client.post("/api/auth/logout").status_code == 204
    assert client.post("/api/auth/login", json={"email": "owner@example.com", "password": "safe-password-123"}).status_code == 200
    assert client.delete(f"/api/pets/{pet_id}").status_code == 204
    assert client.get(f"/api/pets/{pet_id}").status_code == 404
    assert client.get("/api/pets").json() == []
    with sessionmaker(bind=main.engine)() as db:
        assert db.query(Incident).count() == 0
        assert db.query(PetOwner).count() == 0
        assert db.query(Pet).count() == 0
        assert db.query(User).first().password_hash.startswith("$argon2")


def test_first_account_claims_existing_unowned_pets(client):
    with sessionmaker(bind=main.engine)() as db:
        db.add(Pet(name="Legacy", species="Cat"))
        db.commit()

    register(client)
    pets = client.get("/api/pets").json()
    assert len(pets) == 1
    assert pets[0]["name"] == "Legacy"


def png_bytes():
    output = BytesIO()
    Image.new("RGBA", (12, 12), (200, 40, 30, 128)).save(output, format="PNG")
    return output.getvalue()


def heic_bytes():
    output = BytesIO()
    Image.new("RGB", (12, 12), (200, 40, 30)).save(output, format="HEIF")
    return output.getvalue()


def test_image_upload_access_validation_and_cleanup(client, monkeypatch):
    assert client.post(
        "/api/images/prepare",
        files={"file": ("photo.heic", heic_bytes(), "image/heic")},
    ).status_code == 401
    register(client)
    prepared = client.post(
        "/api/images/prepare",
        files={"file": ("photo.heic", heic_bytes(), "image/heic")},
    )
    assert prepared.status_code == 200
    assert prepared.headers["content-type"] == "image/jpeg"
    assert prepared.content.startswith(b"\xff\xd8")
    assert not storage.upload_dir.exists()
    pet_id = client.post("/api/pets", json={"name": "Pixel", "species": "Cat"}).json()["id"]
    pet_upload = client.post(
        f"/api/pets/{pet_id}/image",
        files={"file": ("pixel.png", png_bytes(), "image/png")},
    )
    assert pet_upload.status_code == 200
    pet_url = pet_upload.json()["image_url"]
    assert pet_url.startswith(f"/api/pets/{pet_id}/image?v=")
    pet_image = client.get(pet_url)
    assert pet_image.status_code == 200
    assert pet_image.headers["content-type"] == "image/jpeg"
    assert pet_image.headers["cache-control"] == "private, no-store"
    assert pet_image.content.startswith(b"\xff\xd8")
    heic_upload = client.post(
        f"/api/pets/{pet_id}/image",
        files={"file": ("photo", heic_bytes(), "application/x-apple-photo")},
    )
    assert heic_upload.status_code == 200, heic_upload.text
    assert heic_upload.json()["image_url"] != pet_url
    assert client.get(heic_upload.json()["image_url"]).content.startswith(b"\xff\xd8")
    tiff = BytesIO()
    Image.new("RGB", (12, 12), "red").save(tiff, format="TIFF")
    tiff_upload = client.post(
        f"/api/pets/{pet_id}/image",
        files={"file": ("photo.tiff", tiff.getvalue(), "image/tiff")},
    )
    assert tiff_upload.status_code == 200, tiff_upload.text
    assert client.get(tiff_upload.json()["image_url"]).content.startswith(b"\xff\xd8")
    unusual = BytesIO()
    Image.new("RGB", (12, 12), "red").save(unusual, format="PPM")
    unusual_upload = client.post(
        f"/api/pets/{pet_id}/image",
        files={"file": ("photo", unusual.getvalue(), "application/x-photos-image")},
    )
    assert unusual_upload.status_code == 200, unusual_upload.text

    incident_id = client.post(
        f"/api/pets/{pet_id}/incidents",
        json={"category": "Other", "description": "Suspicious nap", "severity": 1},
    ).json()["id"]
    incident_upload = client.post(
        f"/api/incidents/{incident_id}/image",
        files={"file": ("evidence.png", png_bytes(), "image/png")},
    )
    assert incident_upload.status_code == 200
    incident_url = incident_upload.json()["image_url"]
    assert client.get(incident_url).status_code == 200
    assert storage.image_path("pets", pet_id).is_file()
    assert storage.image_path("incidents", incident_id).is_file()

    unreadable = client.post(
        f"/api/pets/{pet_id}/image",
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert unreadable.status_code == 422
    assert "Export it from Photos as JPEG" in unreadable.json()["detail"]
    assert client.post(
        f"/api/pets/{pet_id}/image",
        files={"file": ("bad.png", b"not an image", "image/png")},
    ).status_code == 422
    with monkeypatch.context() as patch:
        patch.setattr(storage, "MAX_IMAGE_PIXELS", 100)
        too_large = client.post(
            f"/api/pets/{pet_id}/image",
            files={"file": ("large.png", png_bytes(), "image/png")},
        )
    assert too_large.status_code == 422
    assert "50 megapixels" in too_large.json()["detail"]
    assert client.post(
        f"/api/pets/{pet_id}/image",
        files={"file": ("huge.png", b"x" * (storage.MAX_FILE_BYTES + 1), "image/png")},
    ).status_code == 413

    assert client.post("/api/auth/logout").status_code == 204
    register(client, "other@example.com")
    assert client.get(pet_url).status_code == 404
    assert client.get(incident_url).status_code == 404
    assert client.post(
        f"/api/pets/{pet_id}/image",
        files={"file": ("pixel.png", png_bytes(), "image/png")},
    ).status_code == 404

    assert client.post("/api/auth/logout").status_code == 204
    assert client.post("/api/auth/login", json={"email": "owner@example.com", "password": "safe-password-123"}).status_code == 200
    assert client.delete(f"/api/incidents/{incident_id}").status_code == 204
    assert not storage.image_path("incidents", incident_id).exists()
    assert client.delete(f"/api/pets/{pet_id}").status_code == 204
    assert not storage.image_path("pets", pet_id).exists()


def test_reports_api_access_facts_and_provider_fallbacks(client, monkeypatch):
    monkeypatch.setattr(calculator, "utc_now", lambda: datetime(2026, 9, 30))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert client.post("/api/pets/1/reports", json={"period": "weekly"}).status_code == 401
    register(client)
    pet_id = client.post("/api/pets", json={"name": "Pip", "species": "Dog"}).json()["id"]
    assert client.post("/api/pets/999/reports", json={"period": "weekly"}).status_code == 404
    assert client.post(f"/api/pets/{pet_id}/reports", json={"period": "yearly"}).status_code == 422

    incident = client.post(f"/api/pets/{pet_id}/events", json={
        "event_type": "INCIDENT", "category": "Food Theft", "description": "Took a biscuit",
        "severity": 4, "event_time": "2026-09-29T12:00:00Z",
    }).json()
    good = client.post(f"/api/pets/{pet_id}/events", json={
        "event_type": "GOOD_CONDUCT", "category": "Good Behavior", "description": "Sat nicely",
        "event_time": "2026-09-29T13:00:00Z",
    }).json()
    weekly = client.post(f"/api/pets/{pet_id}/reports", json={"period": "weekly"})
    assert weekly.status_code == 200, weekly.text
    body = weekly.json()
    assert body["period_start"] == "2026-09-28T00:00:00Z"
    assert body["period_end"] == "2026-10-05T00:00:00Z"
    assert body["stats"] == {
        "total_events": 2, "incident_count": 1, "good_conduct_count": 1,
        "funny_moment_count": 0, "wellness_count": 0,
        "most_common_incident_category": "Food Theft", "average_incident_severity": 4.0,
        "most_active_event_day": "Tuesday",
    }
    assert [event["id"] for event in body["notable_events"]] == [good["id"], incident["id"]]
    assert body["narrative_source"] == "fallback"

    monthly = client.post(f"/api/pets/{pet_id}/reports", json={"period": "monthly"})
    assert monthly.status_code == 200
    assert monthly.json()["period_start"] == "2026-09-01T00:00:00Z"
    assert monthly.json()["period_end"] == "2026-10-01T00:00:00Z"
    assert monthly.json()["stats"] == body["stats"]

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(report_writer, "write_with_openai", lambda *args: {
        "headline": "Case Notes", "officer_summary": "Pip took a biscuit and also sat nicely.",
        "verdict": "Lovable suspect.", "sentence": "Extra praise.",
    })
    llm = client.post(f"/api/pets/{pet_id}/reports", json={"period": "weekly"}).json()
    assert llm["narrative_source"] == "llm"
    assert llm["headline"] == "Case Notes"
    assert llm["stats"] == body["stats"]

    monkeypatch.setattr(report_writer, "write_with_openai", lambda *args: (_ for _ in ()).throw(TimeoutError()))
    assert client.post(f"/api/pets/{pet_id}/reports", json={"period": "weekly"}).json()["narrative_source"] == "fallback"
    monkeypatch.setattr(report_writer, "write_with_openai", lambda *args: {"headline": "Only one field"})
    assert client.post(f"/api/pets/{pet_id}/reports", json={"period": "weekly"}).json()["narrative_source"] == "fallback"

    assert client.post("/api/auth/logout").status_code == 204
    register(client, "other@example.com")
    assert client.post(f"/api/pets/{pet_id}/reports", json={"period": "weekly"}).status_code == 404
