from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from config import settings
from domain.confirmation_token.models import ConfirmationToken
from domain.user.models import User
from enums.confirmation_token_type import ConfirmationTokenType
from exception.UserExceptions import InvalidConfirmationTokenException, SendEmailException
from security.authentication import (
    TokenType,
    authenticate_user,
    confirm_activation_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    encode_token,
    generate_activation_token,
    get_current_user,
    get_current_user_allow_unactivated,
    hash_password,
    verify_password,
)
from tests.conftest import VALID_USER_PAYLOAD, auth_header, make_user


def _token_for_email(db, email: str) -> ConfirmationToken:
    user = db.query(User).filter(User.email == email).one()
    return db.query(ConfirmationToken).filter(ConfirmationToken.user_id == user.user_id).one()


def test_health(client):
    response = client.get("/auth/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_success(client, db, mock_email):
    response = client.post("/auth/register", json=VALID_USER_PAYLOAD)
    assert response.status_code == 201
    assert mock_email.instances
    created = db.query(User).filter(User.email == VALID_USER_PAYLOAD["email"]).one()
    assert created.activated is False
    assert created.password_hash


def test_register_duplicate_and_integrity(client, monkeypatch):
    assert client.post("/auth/register", json=VALID_USER_PAYLOAD).status_code == 201
    assert client.post("/auth/register", json=VALID_USER_PAYLOAD).status_code == 409

    def boom(*args, **kwargs):
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr("domain.user.repository.create_user", boom)
    payload = {**VALID_USER_PAYLOAD, "email": "other@example.com"}
    assert client.post("/auth/register", json=payload).status_code == 409


def test_register_email_failure(client, monkeypatch):
    class FailingEmail:
        def __init__(self, *args, **kwargs):
            pass

        async def send_activation_email(self):
            raise SendEmailException("smtp down")

    monkeypatch.setattr("routers.auth_router.Email", FailingEmail)
    assert client.post("/auth/register", json=VALID_USER_PAYLOAD).status_code == 503


def test_register_validation(client):
    too_young = {**VALID_USER_PAYLOAD, "dateOfBirth": "2015-01-01"}
    in_future = {**VALID_USER_PAYLOAD, "dateOfBirth": "2999-01-01"}
    short_password = {**VALID_USER_PAYLOAD, "password": "short"}
    assert client.post("/auth/register", json=too_young).status_code == 422
    assert client.post("/auth/register", json=in_future).status_code == 422
    assert client.post("/auth/register", json=short_password).status_code == 422


def test_json_login_sets_cookies(client, db):
    user = make_user(db, email="login@example.com", password="Password123")
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "Password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tokenType"] == "bearer"
    assert body["refreshToken"]
    assert "access_token" in response.cookies
    me = client.get("/auth/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == user.email


def test_form_login_and_failures(client, db):
    user = make_user(db, email="form@example.com", password="Password123")
    ok = client.post("/auth/token", data={"username": user.email, "password": "Password123"})
    assert ok.status_code == 200
    assert (
        client.post(
            "/auth/login", json={"email": user.email, "password": "wrong-password"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/token", data={"username": "missing@example.com", "password": "Password123"}
        ).status_code
        == 401
    )


def test_refresh_from_body_and_cookie(client, db):
    user = make_user(db, email="refresh@example.com")
    refresh = create_refresh_token(user_id=user.user_id)
    body = client.post("/auth/refresh", json={"refreshToken": refresh})
    assert body.status_code == 200
    client.cookies.set("refresh_token", refresh)
    cookie = client.post("/auth/refresh", json={})
    assert cookie.status_code == 200


def test_refresh_missing_and_unknown_user(client, db):
    assert client.post("/auth/refresh", json={}).status_code == 401
    refresh = create_refresh_token(user_id=999999)
    assert client.post("/auth/refresh", json={"refreshToken": refresh}).status_code == 401


def test_logout(client):
    response = client.post("/auth/logout")
    assert response.status_code == 200


def test_verify_email_flow(client, db, monkeypatch):
    client.post("/auth/register", json=VALID_USER_PAYLOAD)
    token_row = db.query(ConfirmationToken).one()
    assert client.get(f"/auth/verify-email/{token_row.token}").status_code == 200
    assert db.query(User).one().activated is True

    assert client.get("/auth/verify-email/missing").status_code == 400

    client.post(
        "/auth/register",
        json={**VALID_USER_PAYLOAD, "email": "second@example.com"},
    )
    token_row = db.query(ConfirmationToken).one()

    def expire(_token):
        raise InvalidConfirmationTokenException("expired")

    monkeypatch.setattr("routers.auth_router.confirm_activation_token", expire)
    assert client.get(f"/auth/verify-email/{token_row.token}").status_code == 400


def test_verify_email_missing_user_and_update_failures(client, db, monkeypatch):
    client.post("/auth/register", json=VALID_USER_PAYLOAD)
    token_row = db.query(ConfirmationToken).one()
    monkeypatch.setattr("domain.user.repository.get_user_by_email", lambda *args, **kwargs: None)
    assert client.get(f"/auth/verify-email/{token_row.token}").status_code == 400
    monkeypatch.undo()

    client.post(
        "/auth/register",
        json={**VALID_USER_PAYLOAD, "email": "third@example.com"},
    )
    token_row = _token_for_email(db, "third@example.com")
    monkeypatch.setattr("domain.user.repository.activate_user", lambda *args, **kwargs: None)
    assert client.get(f"/auth/verify-email/{token_row.token}").status_code == 500

    client.post(
        "/auth/register",
        json={**VALID_USER_PAYLOAD, "email": "fourth@example.com"},
    )
    token_row = _token_for_email(db, "fourth@example.com")
    monkeypatch.setattr(
        "domain.user.repository.activate_user",
        lambda *args, **kwargs: SimpleNamespace(activated=False),
    )
    assert client.get(f"/auth/verify-email/{token_row.token}").status_code == 500


def test_resend_verification(client, db, monkeypatch):
    user = make_user(db, email="resend@example.com", activated=False)
    resend = client.post("/auth/verify-email/resend", headers=auth_header(user.user_id))
    assert resend.status_code == 200
    active = make_user(db, email="already@example.com", activated=True)
    assert (
        client.post("/auth/verify-email/resend", headers=auth_header(active.user_id)).status_code
        == 409
    )

    class FailingEmail:
        def __init__(self, *args, **kwargs):
            pass

        async def send_activation_email(self):
            raise SendEmailException("smtp down")

    monkeypatch.setattr("routers.auth_router.Email", FailingEmail)
    pending = make_user(db, email="resend-fail@example.com", activated=False)
    assert (
        client.post("/auth/verify-email/resend", headers=auth_header(pending.user_id)).status_code
        == 503
    )


def test_password_reset_flow(client, db, monkeypatch):
    unknown = client.post("/auth/password/forgot", json={"email": "nobody@example.com"})
    assert unknown.status_code == 200
    user = make_user(db, email="reset@example.com", password="OldPass123")
    assert client.post("/auth/password/forgot", json={"email": user.email}).status_code == 200
    token_row = db.query(ConfirmationToken).one()
    reset = client.post(
        "/auth/password/reset",
        json={"token": token_row.token, "password": "NewPass123"},
    )
    assert reset.status_code == 200
    login = client.post("/auth/login", json={"email": user.email, "password": "NewPass123"})
    assert login.status_code == 200

    class FailingEmail:
        def __init__(self, *args, **kwargs):
            pass

        async def send_password_reset_email(self):
            raise SendEmailException("smtp down")

    monkeypatch.setattr("routers.auth_router.Email", FailingEmail)
    assert client.post("/auth/password/forgot", json={"email": user.email}).status_code == 200


def test_password_reset_errors(client, db, monkeypatch):
    missing = client.post(
        "/auth/password/reset",
        json={"token": "missing", "password": "NewPass123"},
    )
    assert missing.status_code == 400
    user = make_user(db, email="reset-err@example.com")
    client.post("/auth/password/forgot", json={"email": user.email})
    token_row = db.query(ConfirmationToken).one()

    def expire(_token):
        raise InvalidConfirmationTokenException("expired")

    monkeypatch.setattr("routers.auth_router.confirm_activation_token", expire)
    assert (
        client.post(
            "/auth/password/reset", json={"token": token_row.token, "password": "NewPass123"}
        ).status_code
        == 400
    )


def test_password_reset_missing_user_and_update_failure(client, db, monkeypatch):
    user = make_user(db, email="reset-missing@example.com")
    client.post("/auth/password/forgot", json={"email": user.email})
    token_row = db.query(ConfirmationToken).one()
    monkeypatch.setattr("domain.user.repository.get_user_by_email", lambda *args, **kwargs: None)
    assert (
        client.post(
            "/auth/password/reset", json={"token": token_row.token, "password": "NewPass123"}
        ).status_code
        == 400
    )
    monkeypatch.undo()

    user = make_user(db, email="reset-update@example.com")
    client.post("/auth/password/forgot", json={"email": user.email})
    token_row = db.query(ConfirmationToken).one()
    monkeypatch.setattr("domain.user.repository.update_user_password", lambda *args, **kwargs: None)
    assert (
        client.post(
            "/auth/password/reset", json={"token": token_row.token, "password": "NewPass123"}
        ).status_code
        == 500
    )


def test_me_auth_rules(client, db):
    assert client.get("/auth/users/me").status_code == 401
    user = make_user(db, email="header@example.com")
    me = client.get("/auth/users/me", headers=auth_header(user.user_id))
    assert me.status_code == 200
    assert "passwordHash" not in me.json()
    pending = make_user(db, email="pending@example.com", activated=False)
    assert client.get("/auth/users/me", headers=auth_header(pending.user_id)).status_code == 403


def test_jwt_failures(client, db):
    user = make_user(db, email="jwt@example.com")
    invalid = client.get("/auth/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert invalid.status_code == 401
    expired = create_access_token(user_id=user.user_id, expires=timedelta(seconds=-30))
    expired_response = client.get(
        "/auth/users/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert expired_response.status_code == 401
    refresh = create_refresh_token(user_id=user.user_id)
    refresh_as_access = client.get(
        "/auth/users/me", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert refresh_as_access.status_code == 401
    missing_sub = encode_token({"typ": TokenType.ACCESS.value}, timedelta(minutes=5))
    assert (
        client.get("/auth/users/me", headers={"Authorization": f"Bearer {missing_sub}"}).status_code
        == 401
    )


def test_deleted_user_token(client, db):
    user = make_user(db, email="gone@example.com")
    headers = auth_header(user.user_id)
    db.delete(user)
    db.commit()
    assert client.get("/auth/users/me", headers=headers).status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_dependencies(db):
    user = make_user(db, email="dep@example.com")
    token = create_access_token(user_id=user.user_id)
    current = await get_current_user(token=token, db=db)
    assert current.email == user.email
    pending = make_user(db, email="dep-pending@example.com", activated=False)
    pending_token = create_access_token(user_id=pending.user_id)
    allowed = await get_current_user_allow_unactivated(token=pending_token, db=db)
    assert allowed.email == pending.email
    with pytest.raises(HTTPException):
        await get_current_user(token=pending_token, db=db)


def test_password_helpers_and_tokens():
    assert verify_password("secret", "not-a-hash") is False
    hashed = hash_password("Password123")
    assert verify_password("Password123", hashed) is True
    with pytest.raises(HTTPException):
        decode_token(
            jwt.encode(
                {"sub": ["nope"], "typ": "access", "exp": datetime.now(UTC) + timedelta(minutes=5)},
                settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
            ),
            expected_type=TokenType.ACCESS,
        )
    with pytest.raises(HTTPException):
        decode_token(
            encode_token({"sub": "abc", "typ": TokenType.ACCESS.value}, timedelta(minutes=5)),
            expected_type=TokenType.ACCESS,
        )


def test_authenticate_user_null_hash(db, monkeypatch):
    monkeypatch.setattr(
        "domain.user.repository.get_user_by_email",
        lambda *args, **kwargs: SimpleNamespace(password_hash=None),
    )
    assert authenticate_user(db, "null-hash@example.com", "Password123") is None


def test_confirm_activation_token_roundtrip():
    salt = "abc"
    token = generate_activation_token("roundtrip@example.com", salt)
    parsed = confirm_activation_token(
        ConfirmationToken(
            user_id=1,
            token=token,
            token_salt=salt,
            token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
            max_age=1200,
        )
    )
    assert parsed == "roundtrip@example.com"
    with pytest.raises(InvalidConfirmationTokenException):
        confirm_activation_token(
            ConfirmationToken(
                user_id=1,
                token="totally-invalid",
                token_salt="salt",
                token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
                max_age=1200,
            )
        )
