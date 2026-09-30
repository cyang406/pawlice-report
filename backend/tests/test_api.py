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
