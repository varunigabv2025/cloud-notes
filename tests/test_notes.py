from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_notes_crud(client: TestClient) -> None:
    assert client.get("/").status_code == 200
    assert client.get("/api/notes").json() == []
    created = client.post("/api/notes", json={"title": "First note", "content": "A thought"})
    assert created.status_code == 201
    note = created.json()
    assert client.get(f"/api/notes/{note['id']}").json()["title"] == "First note"
    updated = client.put(f"/api/notes/{note['id']}", json={"title": "Revised", "content": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Revised"
    assert client.delete(f"/api/notes/{note['id']}").status_code == 204
    assert client.get(f"/api/notes/{note['id']}").status_code == 404


def test_validation(client: TestClient) -> None:
    response = client.post("/api/notes", json={"title": "   ", "content": "x"})
    assert response.status_code == 422
