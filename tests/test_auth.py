from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import User

CREDENTIALS = {"email": "ayan@example.com", "password": "supersecret1"}


def test_register_creates_user(client):
    response = client.post("/auth/register", json=CREDENTIALS)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ayan@example.com"
    assert "password" not in body and "password_hash" not in body


def test_password_is_stored_as_argon2_hash_not_plain_text(client):
    client.post("/auth/register", json=CREDENTIALS)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "ayan@example.com"))
    assert user.password_hash != CREDENTIALS["password"]
    assert user.password_hash.startswith("$argon2")


def test_register_lowercases_email(client):
    response = client.post("/auth/register", json={**CREDENTIALS, "email": "Ayan@Example.COM"})
    assert response.json()["email"] == "ayan@example.com"


def test_register_duplicate_email_is_rejected_case_insensitively(client):
    client.post("/auth/register", json=CREDENTIALS)
    response = client.post("/auth/register", json={**CREDENTIALS, "email": "AYAN@example.com"})
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post("/auth/register", json={**CREDENTIALS, "password": "short"})
    assert response.status_code == 422


def test_register_rejects_invalid_email(client):
    response = client.post("/auth/register", json={**CREDENTIALS, "email": "not-an-email"})
    assert response.status_code == 422


def test_login_returns_token(client):
    client.post("/auth/register", json=CREDENTIALS)
    response = client.post(
        "/auth/login",
        data={"username": CREDENTIALS["email"], "password": CREDENTIALS["password"]},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password_and_unknown_user_give_same_error(client):
    client.post("/auth/register", json=CREDENTIALS)
    wrong_password = client.post(
        "/auth/login", data={"username": CREDENTIALS["email"], "password": "wrong-password"}
    )
    unknown_user = client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": "wrong-password"}
    )
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_me_with_valid_token(client, make_user):
    headers = make_user("ayan@example.com")
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "ayan@example.com"


def test_me_without_token_is_unauthorized(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_garbage_token_is_unauthorized(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert response.status_code == 401


def _token(user_id: int, *, secret: str, expires_in: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def test_expired_token_is_rejected(client, make_user):
    make_user()
    token = _token(1, secret=settings.secret_key, expires_in=timedelta(minutes=-1))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_token_signed_with_wrong_secret_is_rejected(client, make_user):
    make_user()
    token = _token(1, secret="some-other-secret-key-of-32-bytes!!", expires_in=timedelta(hours=1))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_token_for_deleted_user_is_rejected(client):
    token = _token(999, secret=settings.secret_key, expires_in=timedelta(hours=1))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
