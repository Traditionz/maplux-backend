from domain.user.models import User
from domain.user_suspension.repository import create_user_suspension_short
from tests.conftest import ADDRESS_PAYLOAD, auth_header, make_user


def test_update_current_user(client, db):
    user = make_user(db, email="patch@example.com")
    response = client.patch(
        "/auth/users/me",
        json={"firstName": "Janet"},
        headers=auth_header(user.user_id),
    )
    assert response.status_code == 200
    assert response.json()["firstName"] == "Janet"
    assert (
        client.patch(
            "/auth/users/me",
            json={"dateOfBirth": "2015-01-01"},
            headers=auth_header(user.user_id),
        ).status_code
        == 422
    )


def test_update_current_user_missing(client, db, monkeypatch):
    user = make_user(db, email="patch-missing@example.com")
    monkeypatch.setattr("domain.user.repository.update_user_profile", lambda *args, **kwargs: None)
    assert (
        client.patch(
            "/auth/users/me", json={"lastName": "Smith"}, headers=auth_header(user.user_id)
        ).status_code
        == 404
    )


def test_address_upsert_and_get(client, db):
    user = make_user(db, email="address@example.com")
    headers = auth_header(user.user_id)
    assert client.get("/auth/users/me/address", headers=headers).status_code == 404
    created = client.put("/auth/users/me/address", json=ADDRESS_PAYLOAD, headers=headers)
    assert created.status_code == 200
    assert created.json()["city"] == "Austin"
    updated = client.put(
        "/auth/users/me/address",
        json={**ADDRESS_PAYLOAD, "city": "Dallas"},
        headers=headers,
    )
    assert updated.json()["city"] == "Dallas"
    fetched = client.get("/auth/users/me/address", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["city"] == "Dallas"


def test_image_upsert_and_get(client, db):
    user = make_user(db, email="image@example.com")
    headers = auth_header(user.user_id)
    assert client.get("/auth/users/me/image", headers=headers).status_code == 404
    created = client.put("/auth/users/me/image", json={"imageExt": ".PNG"}, headers=headers)
    assert created.status_code == 200
    assert created.json()["imageExt"] == "png"
    updated = client.put("/auth/users/me/image", json={"imageExt": "jpg"}, headers=headers)
    assert updated.json()["imageExt"] == "jpg"
    fetched = client.get("/auth/users/me/image", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["imageExt"] == "jpg"
    rejected = client.put("/auth/users/me/image", json={"imageExt": "exe"}, headers=headers)
    assert rejected.status_code == 422


def test_get_user_public_profile(client, db):
    user = make_user(db, email="public@example.com")
    other = make_user(db, email="other@example.com", first_name="Ada")
    response = client.get(f"/auth/users/{other.user_id}", headers=auth_header(user.user_id))
    assert response.status_code == 200
    assert response.json()["firstName"] == "Ada"
    assert "email" not in response.json()
    assert client.get("/auth/users/999999", headers=auth_header(user.user_id)).status_code == 404


def test_suspend_requires_admin_and_blocks_user(client, db):
    member = make_user(db, email="member@example.com")
    target = make_user(db, email="target@example.com")
    assert (
        client.post(
            f"/auth/users/{target.user_id}/suspensions",
            json={"durationDays": 5},
            headers=auth_header(member.user_id),
        ).status_code
        == 403
    )
    admin = make_user(db, email="admin@example.com", is_admin=True)
    assert (
        client.post(
            "/auth/users/999999/suspensions",
            json={"durationDays": 5},
            headers=auth_header(admin.user_id),
        ).status_code
        == 404
    )
    suspended = client.post(
        f"/auth/users/{target.user_id}/suspensions",
        json={"durationDays": 5},
        headers=auth_header(admin.user_id),
    )
    assert suspended.status_code == 200
    assert client.get("/auth/users/me", headers=auth_header(target.user_id)).status_code == 403
    indefinite = make_user(db, email="forever@example.com")
    assert (
        client.post(
            f"/auth/users/{indefinite.user_id}/suspensions",
            json={"durationDays": 36525},
            headers=auth_header(admin.user_id),
        ).status_code
        == 200
    )


def test_expired_suspension_allows_access(client, db):
    user = make_user(db, email="was-suspended@example.com")
    suspension = create_user_suspension_short(db, user.user_id)
    suspension.expiration_date = suspension.expiration_date.replace(year=2000)
    db.commit()
    assert client.get("/auth/users/me", headers=auth_header(user.user_id)).status_code == 200
    assert db.get(User, user.user_id) is not None
