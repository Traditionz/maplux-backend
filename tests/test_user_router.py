from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from config import settings
from domain.confirmation_token.models import ConfirmationToken
from domain.user.models import User
from domain.user_suspension.repository import create_user_suspension_short
from enums.confirmation_token_type import ConfirmationTokenType
from exception.UserExceptions import InvalidConfirmationTokenException, SendEmailException
from security.authentication import (
    authenticate_user,
    check_password,
    confirm_activation_token,
    create_access_token,
    decode_access_token,
    generate_activation_token,
    get_current_user,
    get_current_user_allow_unactivated,
    hash_password,
)
from tests.conftest import ADDRESS_PAYLOAD, VALID_USER_PAYLOAD, auth_header, make_user


def test_home(client):
    response = client.get("/auth/home")
    assert response.status_code == 200
    assert response.json() == ["Hello"]


def test_create_user_success(client, db, mock_email):
    response = client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["status"] == "success"
    assert mock_email.instances
    created = db.query(User).filter(User.email == VALID_USER_PAYLOAD["email"]).one()
    assert created.activated is False
    assert created.phone_number == VALID_USER_PAYLOAD["phoneNumber"]
    assert created.password_hashed is not None


def test_create_user_duplicate_email(client):
    first = client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    assert first.status_code == 201
    second = client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    assert second.status_code == 409
    assert second.json()["errors"] == ["Email already registered."]


def test_create_user_integrity_error(client, monkeypatch):
    def boom(*args, **kwargs):
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr("domain.user.repository.create_user", boom)
    response = client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    assert response.status_code == 409


def test_create_user_email_failure(client, monkeypatch):
    class FailingEmail:
        def __init__(self, *args, **kwargs):
            pass

        async def send_activation_email(self):
            raise SendEmailException("smtp down")

    monkeypatch.setattr("routers.user_router.Email", FailingEmail)
    response = client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    assert response.status_code == 503


def test_create_user_validation(client):
    underage = {**VALID_USER_PAYLOAD, "dateOfBirth": "2015-01-01"}
    assert client.post("/auth/users/", json=underage).status_code == 422

    future = {**VALID_USER_PAYLOAD, "dateOfBirth": "2999-01-01"}
    assert client.post("/auth/users/", json=future).status_code == 422

    short_password = {**VALID_USER_PAYLOAD, "password": "short"}
    assert client.post("/auth/users/", json=short_password).status_code == 422


def test_login_and_cookie_auth(client, db):
    user = make_user(db, email="login@example.com", password="Password123")
    response = client.post(
        "/auth/login/",
        data={"username": user.email, "password": "Password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tokenType"] == "bearer"
    assert "accessToken" in body
    assert "Authorization" in response.cookies

    me = client.get("/auth/users/me/")
    assert me.status_code == 200
    assert me.json()["email"] == user.email


def test_login_bad_password(client, db):
    user = make_user(db, email="badpass@example.com")
    response = client.post(
        "/auth/login/",
        data={"username": user.email, "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post(
        "/auth/login/",
        data={"username": "missing@example.com", "password": "Password123"},
    )
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/auth/users/me/")
    assert response.status_code == 401


def test_me_with_bearer_header(client, db):
    user = make_user(db, email="header@example.com")
    response = client.get("/auth/users/me/", headers=auth_header(user.email))
    assert response.status_code == 200
    assert response.json()["firstName"] == "Jane"
    assert "passwordHashed" not in response.json()


def test_unactivated_user_cannot_access_me(client, db):
    user = make_user(db, email="pending@example.com", activated=False)
    response = client.get("/auth/users/me/", headers=auth_header(user.email))
    assert response.status_code == 403
    assert response.json()["errors"] == ["Account is not activated."]


def test_resend_activation(client, db, mock_email):
    user = make_user(db, email="resend@example.com", activated=False)
    response = client.put(
        "/auth/users/me/activate/resend/",
        headers=auth_header(user.email),
    )
    assert response.status_code == 200
    assert mock_email.instances


def test_resend_activation_already_active(client, db):
    user = make_user(db, email="active@example.com", activated=True)
    response = client.put(
        "/auth/users/me/activate/resend/",
        headers=auth_header(user.email),
    )
    assert response.status_code == 409


def test_resend_activation_email_failure(client, db, monkeypatch):
    user = make_user(db, email="resend-fail@example.com", activated=False)

    class FailingEmail:
        def __init__(self, *args, **kwargs):
            pass

        async def send_activation_email(self):
            raise SendEmailException("smtp down")

    monkeypatch.setattr("routers.user_router.Email", FailingEmail)
    response = client.put(
        "/auth/users/me/activate/resend/",
        headers=auth_header(user.email),
    )
    assert response.status_code == 503


def test_activate_user_success(client, db):
    client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    token_row = db.query(ConfirmationToken).one()
    response = client.get(f"/auth/users/me/activate/{token_row.token}")
    assert response.status_code == 200
    user = db.query(User).filter(User.email == VALID_USER_PAYLOAD["email"]).one()
    assert user.activated is True
    assert db.query(ConfirmationToken).count() == 0


def test_activate_user_unknown_token(client):
    response = client.get("/auth/users/me/activate/not-a-real-token")
    assert response.status_code == 400


def test_activate_user_expired_token(client, db, monkeypatch):
    client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    token_row = db.query(ConfirmationToken).one()

    def expire(_token):
        raise InvalidConfirmationTokenException("expired")

    monkeypatch.setattr("routers.user_router.confirm_activation_token", expire)
    response = client.get(f"/auth/users/me/activate/{token_row.token}")
    assert response.status_code == 400


def test_activate_user_missing_account(client, db, monkeypatch):
    client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    token_row = db.query(ConfirmationToken).one()
    monkeypatch.setattr("domain.user.repository.get_user_by_email", lambda *args, **kwargs: None)
    response = client.get(f"/auth/users/me/activate/{token_row.token}")
    assert response.status_code == 400


def test_activate_user_update_failure(client, db, monkeypatch):
    client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    token_row = db.query(ConfirmationToken).one()
    monkeypatch.setattr("domain.user.repository.activate_user", lambda *args, **kwargs: None)
    response = client.get(f"/auth/users/me/activate/{token_row.token}")
    assert response.status_code == 500


def test_activate_user_not_marked_active(client, db, monkeypatch):
    client.post("/auth/users/", json=VALID_USER_PAYLOAD)
    token_row = db.query(ConfirmationToken).one()
    monkeypatch.setattr(
        "domain.user.repository.activate_user",
        lambda *args, **kwargs: SimpleNamespace(activated=False),
    )
    response = client.get(f"/auth/users/me/activate/{token_row.token}")
    assert response.status_code == 500


def test_forgot_password_unknown_email(client):
    response = client.post(
        "/auth/users/me/password/forgot/",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200
    assert "password reset email" in response.json()["message"]


def test_forgot_and_reset_password(client, db):
    user = make_user(db, email="reset@example.com", password="OldPass123")
    forgot = client.post(
        "/auth/users/me/password/forgot/",
        json={"email": user.email},
    )
    assert forgot.status_code == 200
    token_row = db.query(ConfirmationToken).one()
    reset = client.patch(
        f"/auth/users/me/password/reset/{token_row.token}",
        json={"password": "NewPass123"},
    )
    assert reset.status_code == 200
    login = client.post(
        "/auth/login/",
        data={"username": user.email, "password": "NewPass123"},
    )
    assert login.status_code == 200


def test_forgot_password_email_failure(client, db, monkeypatch):
    user = make_user(db, email="reset-fail@example.com")

    class FailingEmail:
        def __init__(self, *args, **kwargs):
            pass

        async def send_password_reset_email(self):
            raise SendEmailException("smtp down")

    monkeypatch.setattr("routers.user_router.Email", FailingEmail)
    response = client.post(
        "/auth/users/me/password/forgot/",
        json={"email": user.email},
    )
    assert response.status_code == 200


def test_reset_password_unknown_token(client):
    response = client.patch(
        "/auth/users/me/password/reset/missing",
        json={"password": "NewPass123"},
    )
    assert response.status_code == 400


def test_reset_password_expired_token(client, db, monkeypatch):
    user = make_user(db, email="reset-expired@example.com")
    client.post("/auth/users/me/password/forgot/", json={"email": user.email})
    token_row = db.query(ConfirmationToken).one()

    def expire(_token):
        raise InvalidConfirmationTokenException("expired")

    monkeypatch.setattr("routers.user_router.confirm_activation_token", expire)
    response = client.patch(
        f"/auth/users/me/password/reset/{token_row.token}",
        json={"password": "NewPass123"},
    )
    assert response.status_code == 400


def test_reset_password_missing_user(client, db, monkeypatch):
    user = make_user(db, email="reset-missing@example.com")
    client.post("/auth/users/me/password/forgot/", json={"email": user.email})
    token_row = db.query(ConfirmationToken).one()
    monkeypatch.setattr("domain.user.repository.get_user_by_email", lambda *args, **kwargs: None)
    response = client.patch(
        f"/auth/users/me/password/reset/{token_row.token}",
        json={"password": "NewPass123"},
    )
    assert response.status_code == 400


def test_reset_password_update_failure(client, db, monkeypatch):
    user = make_user(db, email="reset-update@example.com")
    client.post("/auth/users/me/password/forgot/", json={"email": user.email})
    token_row = db.query(ConfirmationToken).one()
    monkeypatch.setattr("domain.user.repository.update_user_password", lambda *args, **kwargs: None)
    response = client.patch(
        f"/auth/users/me/password/reset/{token_row.token}",
        json={"password": "NewPass123"},
    )
    assert response.status_code == 500


def test_logout(client):
    response = client.post("/auth/users/me/logout/")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_address_create_update_and_conflict(client, db):
    user = make_user(db, email="address@example.com")
    headers = auth_header(user.email)
    created = client.post("/auth/users/me/address/", json=ADDRESS_PAYLOAD, headers=headers)
    assert created.status_code == 200
    conflict = client.post("/auth/users/me/address/", json=ADDRESS_PAYLOAD, headers=headers)
    assert conflict.status_code == 409
    updated = client.put(
        "/auth/users/me/address/",
        json={**ADDRESS_PAYLOAD, "city": "Dallas"},
        headers=headers,
    )
    assert updated.status_code == 200


def test_update_address_missing(client, db):
    user = make_user(db, email="no-address@example.com")
    response = client.put(
        "/auth/users/me/address/",
        json=ADDRESS_PAYLOAD,
        headers=auth_header(user.email),
    )
    assert response.status_code == 404


def test_user_image_create_update_and_conflict(client, db):
    user = make_user(db, email="image@example.com")
    headers = auth_header(user.email)
    created = client.post(
        "/auth/users/me/profile/image/", json={"imageExt": ".PNG"}, headers=headers
    )
    assert created.status_code == 200
    conflict = client.post(
        "/auth/users/me/profile/image/", json={"imageExt": "png"}, headers=headers
    )
    assert conflict.status_code == 409
    updated = client.put(
        "/auth/users/me/profile/image/", json={"imageExt": "jpg"}, headers=headers
    )
    assert updated.status_code == 200


def test_update_image_missing(client, db):
    user = make_user(db, email="no-image@example.com")
    response = client.put(
        "/auth/users/me/profile/image/",
        json={"imageExt": "png"},
        headers=auth_header(user.email),
    )
    assert response.status_code == 404


def test_invalid_image_extension(client, db):
    user = make_user(db, email="bad-image@example.com")
    response = client.post(
        "/auth/users/me/profile/image/",
        json={"imageExt": "exe"},
        headers=auth_header(user.email),
    )
    assert response.status_code == 422


def test_get_user_public_profile(client, db):
    user = make_user(db, email="public@example.com")
    other = make_user(db, email="other@example.com", first_name="Ada")
    response = client.get(f"/auth/users/{other.user_id}", headers=auth_header(user.email))
    assert response.status_code == 200
    body = response.json()
    assert body["firstName"] == "Ada"
    assert "email" not in body


def test_get_user_not_found(client, db):
    user = make_user(db, email="lookup@example.com")
    response = client.get("/auth/users/999999", headers=auth_header(user.email))
    assert response.status_code == 404


def test_suspend_requires_admin(client, db):
    user = make_user(db, email="member@example.com")
    target = make_user(db, email="target@example.com")
    response = client.post(
        f"/auth/users/{target.user_id}/suspend/temporary/",
        headers=auth_header(user.email),
    )
    assert response.status_code == 403


def test_suspend_user_not_found(client, db):
    admin = make_user(db, email="admin-missing@example.com", is_admin=True)
    response = client.post(
        "/auth/users/999999/suspend/temporary/",
        headers=auth_header(admin.email),
    )
    assert response.status_code == 404


def test_suspend_and_blocked_access(client, db):
    admin = make_user(db, email="admin@example.com", is_admin=True)
    target = make_user(db, email="suspended@example.com")
    response = client.post(
        f"/auth/users/{target.user_id}/suspend/temporary/",
        headers=auth_header(admin.email),
    )
    assert response.status_code == 200
    blocked = client.get("/auth/users/me/", headers=auth_header(target.email))
    assert blocked.status_code == 403
    assert blocked.json()["errors"] == ["User is suspended."]


def test_expired_suspension_allows_access(client, db):
    user = make_user(db, email="was-suspended@example.com")
    suspension = create_user_suspension_short(db, user.user_id)
    suspension.expiration_date = suspension.expiration_date.replace(year=2000)
    db.commit()
    response = client.get("/auth/users/me/", headers=auth_header(user.email))
    assert response.status_code == 200


def test_invalid_and_expired_jwt(client, db):
    user = make_user(db, email="jwt@example.com")
    assert client.get(
        "/auth/users/me/", headers={"Authorization": "Bearer not-a-jwt"}
    ).status_code == 401
    expired = create_access_token({"sub": user.email}, expires=timedelta(seconds=-30))
    assert client.get(
        "/auth/users/me/", headers={"Authorization": f"Bearer {expired}"}
    ).status_code == 401
    missing_sub = create_access_token({"role": "user"})
    assert client.get(
        "/auth/users/me/", headers={"Authorization": f"Bearer {missing_sub}"}
    ).status_code == 401


def test_deleted_user_token(client, db):
    user = make_user(db, email="gone@example.com")
    headers = auth_header(user.email)
    db.delete(user)
    db.commit()
    response = client.get("/auth/users/me/", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_dependencies(db):
    user = make_user(db, email="dep@example.com")
    token = create_access_token({"sub": user.email})
    current = await get_current_user(token=token, db=db)
    assert current.email == user.email
    pending = make_user(db, email="dep-pending@example.com", activated=False)
    pending_token = create_access_token({"sub": pending.email})
    allowed = await get_current_user_allow_unactivated(token=pending_token, db=db)
    assert allowed.email == pending.email
    with pytest.raises(HTTPException):
        await get_current_user(token=pending_token, db=db)


def test_authenticate_user_null_hash(db, monkeypatch):
    monkeypatch.setattr(
        "domain.user.repository.get_user_by_email",
        lambda *args, **kwargs: SimpleNamespace(password_hashed=None),
    )
    assert authenticate_user(db, "null-hash@example.com", "Password123") is None


def test_check_password_invalid_values():
    assert check_password(b"secret", b"not-a-bcrypt-hash") is False
    assert check_password("secret", hash_password("secret")[1]) is False  # type: ignore[arg-type]


def test_confirm_activation_token_bad_signature():
    token = ConfirmationToken(
        user_id=1,
        token="totally-invalid",
        token_salt="salt",
        token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
        max_age=1200,
    )
    with pytest.raises(InvalidConfirmationTokenException):
        confirm_activation_token(token)


def test_generate_activation_token_roundtrip():
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


def test_decode_access_token_non_string_sub():
    token = jwt.encode(
        {
            "sub": ["not-a-string"],
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException):
        decode_access_token(token)
