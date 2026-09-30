import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SESSION_SECRET", "test-session-secret-longer-than-thirty-two-characters")

from app import main
from app.database import Base, get_db
from app.models import Incident, Pet, PetOwner, User


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
    from app import storage
    monkeypatch.setattr(storage, "upload_dir", tmp_path / "uploads")
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
                "image_url": "evidence.jpg",
            },
        )
        assert response.status_code == 201
        assert response.json()["image_url"] == "evidence.jpg"
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


from io import BytesIO
from PIL import Image
from app import storage


def png_bytes():
    output = BytesIO()
    Image.new("RGB", (12, 12), "red").save(output, format="PNG")
    return output.getvalue()


def test_image_upload(client):
    register(client)
    pet_id = client.post("/api/pets", json={"name": "Pixel", "species": "Cat"}).json()["id"]
    response = client.post(f"/api/pets/{pet_id}/image", files={"file": ("pixel.png", png_bytes(), "image/png")})
    assert response.status_code == 200
    assert client.get(response.json()["image_url"]).content.startswith(b"\xff\xd8")
    assert storage.image_path("pets", pet_id).exists()
    assert client.delete(f"/api/pets/{pet_id}").status_code == 204
    assert not storage.image_path("pets", pet_id).exists()
