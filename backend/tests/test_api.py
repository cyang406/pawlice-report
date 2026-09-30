from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db


def test_pet_incident_and_stats(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def test_db():
        with sessions() as session:
            yield session

    main.app.dependency_overrides[get_db] = test_db
    monkeypatch.setattr(main, "engine", engine)
    try:
        with TestClient(main.app) as client:
            assert client.get("/api/health").json() == {"status": "ok"}
            pet = client.post("/api/pets", json={"name": "Mochi", "species": "Cat"})
            assert pet.status_code == 201
            pet_id = pet.json()["id"]
            assert len(client.get("/api/pets").json()) == 1
            assert client.get(f"/api/pets/{pet_id}").json()["name"] == "Mochi"
            incident = client.post(f"/api/pets/{pet_id}/incidents", json={
                "category": "Food Theft", "description": "Stole a sandwich", "severity": 2,
            })
            assert incident.status_code == 201
            assert client.get(f"/api/pets/{pet_id}/stats").json()["total_incidents"] == 1
            assert len(client.get(f"/api/pets/{pet_id}/incidents").json()) == 1
            assert client.delete(f"/api/incidents/{incident.json()['id']}").status_code == 204
            assert client.get(f"/api/pets/{pet_id}/stats").json()["total_incidents"] == 0
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
