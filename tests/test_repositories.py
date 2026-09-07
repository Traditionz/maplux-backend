from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from domain.address import repository as address_repository
from domain.address.schemas import AddressCreateSchema
from domain.confirmation_token import repository as token_repository
from domain.confirmation_token.schemas import ConfirmationTokenCreateSchema
from domain.user import repository as user_repository
from domain.user.schemas import UserUpdateSchema
from domain.user_image import repository as image_repository
from domain.user_image.schemas import UserImageCreateSchema
from domain.user_suspension import repository as suspension_repository
from domain.user_suspension.schemas import UserSuspensionBaseSchema
from enums.confirmation_token_type import ConfirmationTokenType
from tests.conftest import make_user


def test_user_repository_helpers(db):
    first = make_user(db, email="one@example.com")
    make_user(db, email="two@example.com")
    assert user_repository.get_user(db, first.user_id).email == first.email
    assert user_repository.get_user_by_email(db, "missing@example.com") is None
    assert len(user_repository.get_users(db)) == 2
    assert user_repository.activate_user(db, 999) is None
    assert user_repository.update_user_password(db, 999, "hash") is None
    assert user_repository.update_user_profile(db, 999, UserUpdateSchema()) is None
    updated_profile = user_repository.update_user_profile(
        db, first.user_id, UserUpdateSchema(first_name="Janet")
    )
    assert updated_profile.first_name == "Janet"


def test_address_repository_helpers(db):
    user = make_user(db, email="addr-repo@example.com")
    payload = AddressCreateSchema(
        street_address="1 Road",
        city="Austin",
        state_province="TX",
        postal_zip="78701",
        country="US",
    )
    created = address_repository.create_address(db, user.user_id, payload)
    assert created.apt_suite is None
    assert address_repository.get_address(db, user.user_id).city == "Austin"
    updated = address_repository.update_address(
        db,
        user.user_id,
        payload.model_copy(update={"city": "Dallas"}),
    )
    assert updated.city == "Dallas"
    assert address_repository.update_address(db, 999, payload) is None
    upserted = address_repository.upsert_address(
        db, user.user_id, payload.model_copy(update={"city": "Houston"})
    )
    assert upserted.city == "Houston"
    other = make_user(db, email="addr-upsert@example.com")
    created = address_repository.upsert_address(db, other.user_id, payload)
    assert created.city == "Austin"


def test_image_repository_helpers(db):
    user = make_user(db, email="img-repo@example.com")
    payload = UserImageCreateSchema(image_ext="png")
    image_repository.create_user_image(db, user.user_id, payload)
    assert image_repository.get_user_image(db, user.user_id).image_ext == "png"
    updated = image_repository.update_user_image(
        db, user.user_id, UserImageCreateSchema(image_ext="jpg")
    )
    assert updated.image_ext == "jpg"
    assert image_repository.update_user_image(db, 999, payload) is None
    upserted = image_repository.upsert_user_image(
        db, user.user_id, UserImageCreateSchema(image_ext="webp")
    )
    assert upserted.image_ext == "webp"
    other = make_user(db, email="img-upsert@example.com")
    created = image_repository.upsert_user_image(
        db, other.user_id, UserImageCreateSchema(image_ext="gif")
    )
    assert created.image_ext == "gif"


def test_confirmation_token_repository_helpers(db):
    user = make_user(db, email="token-repo@example.com")
    schema = ConfirmationTokenCreateSchema(
        user_id=user.user_id,
        token="token-one",
        token_salt="salt",
        token_type=ConfirmationTokenType.ACCOUNT_ACTIVATION,
        max_age=1200,
    )
    token_repository.create_confirmation_token(db, schema)
    found = token_repository.get_confirmation_token(
        db, "token-one", ConfirmationTokenType.ACCOUNT_ACTIVATION
    )
    assert found is not None
    assert (
        token_repository.get_confirmation_token(
            db, "missing", ConfirmationTokenType.ACCOUNT_ACTIVATION
        )
        is None
    )
    assert (
        token_repository.delete_confirmation_token(
            db, "token-one", ConfirmationTokenType.ACCOUNT_ACTIVATION
        )
        == 1
    )
    token_repository.create_confirmation_token(db, schema)
    assert (
        token_repository.delete_confirmation_tokens_for_user(
            db, user.user_id, ConfirmationTokenType.ACCOUNT_ACTIVATION
        )
        == 1
    )
    assert (
        token_repository.delete_confirmation_tokens_for_user(
            db, user.user_id, ConfirmationTokenType.ACCOUNT_ACTIVATION
        )
        == 0
    )


def test_suspension_repository_helpers(db):
    user = make_user(db, email="suspend-repo@example.com")
    assert suspension_repository.is_suspension_active(None) is False
    first = suspension_repository.create_user_suspension_short(db, user.user_id)
    second = suspension_repository.create_user_suspension_short(db, user.user_id)
    assert first.user_id == second.user_id
    five_day_expiration = second.expiration_date
    indefinite = suspension_repository.create_user_suspension_indefinite(db, user.user_id)
    assert indefinite.expiration_date > five_day_expiration
    updated = suspension_repository.update_user_suspension(
        db,
        UserSuspensionBaseSchema(
            user_id=user.user_id,
            expiration_date=datetime(2001, 1, 1),
        ),
    )
    assert updated.expiration_date.year == 2001
    assert (
        suspension_repository.update_user_suspension(
            db,
            UserSuspensionBaseSchema(user_id=999, expiration_date=datetime(2001, 1, 1)),
        )
        is None
    )

    active = SimpleNamespace(expiration_date=datetime.now(UTC) + timedelta(days=1))
    expired = SimpleNamespace(expiration_date=datetime.now(UTC) - timedelta(days=1))
    naive_active = SimpleNamespace(
        expiration_date=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)
    )
    assert suspension_repository.is_suspension_active(active) is True
    assert suspension_repository.is_suspension_active(expired) is False
    assert suspension_repository.is_suspension_active(naive_active) is True
