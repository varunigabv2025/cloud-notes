import os
from collections.abc import Generator

os.environ.setdefault("SECRET_KEY", "test-secret-not-for-production")

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


def signup(client: TestClient, name: str, email: str, password: str = "password123") -> dict:
    response = client.post("/api/auth/signup", json={
        "name": name, "email": email, "password": password, "confirm_password": password,
    })
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str, password: str = "password123") -> dict:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_signup_validation_and_duplicate_email(client: TestClient) -> None:
    user = signup(client, "Ada", "ADA@example.com")
    assert user["email"] == "ada@example.com"
    assert "password_hash" not in user
    assert client.post("/api/auth/signup", json={"name": "Ada", "email": "ada@example.com", "password": "password123", "confirm_password": "password123"}).status_code == 409
    assert client.post("/api/auth/signup", json={"name": "", "email": "not-an-email", "password": "short", "confirm_password": "different"}).status_code == 422


def test_login_me_and_logout(client: TestClient) -> None:
    signup(client, "Ada", "ada@example.com")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong"}).status_code == 401
    assert login(client, "ada@example.com")["name"] == "Ada"
    assert client.get("/api/auth/me").json()["email"] == "ada@example.com"
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_notes_crud_requires_login_and_is_user_scoped(client: TestClient) -> None:
    assert client.get("/api/notes").status_code == 401
    signup(client, "User One", "one@example.com")
    login(client, "one@example.com")
    created = client.post("/api/notes", json={"title": "Private", "content": "Only user one"})
    assert created.status_code == 201
    note_id = created.json()["id"]
    assert client.get("/api/notes").json()[0]["id"] == note_id
    assert client.put(f"/api/notes/{note_id}", json={"title": "Edited", "content": "Updated"}).json()["title"] == "Edited"
    assert client.post("/api/auth/logout").status_code == 204
    signup(client, "User Two", "two@example.com")
    login(client, "two@example.com")
    assert client.get("/api/notes").json() == []
    assert client.get(f"/api/notes/{note_id}").status_code == 404
    assert client.put(f"/api/notes/{note_id}", json={"title": "No", "content": ""}).status_code == 404
    assert client.delete(f"/api/notes/{note_id}").status_code == 404
    own_note = client.post("/api/notes", json={"title": "User two", "content": "Private"}).json()
    assert own_note["title"] == "User two"
    assert client.post("/api/auth/logout").status_code == 204
    login(client, "one@example.com")
    assert [note["id"] for note in client.get("/api/notes").json()] == [note_id]
    assert client.delete(f"/api/notes/{note_id}").status_code == 204
    assert client.get("/api/notes").json() == []
