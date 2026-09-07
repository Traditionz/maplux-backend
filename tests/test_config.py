from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from config import Settings
from domain.user.schemas import UserCreateSchema, UserUpdateSchema, _age_on
from enums.confirmation_token_type import ConfirmationTokenType


def _settings_kwargs(**overrides):
    data = {
        "app_name": "Maplux",
        "client_origin": "http://localhost:8000",
        "database_url": "sqlite://",
        "activate_secret_key": "activate-secret-key",
        "jwt_secret_key": "jwt-secret-key",
        "email_username": "user",
        "email_password": "pass",
        "email_from": "maplux@example.com",
    }
    data.update(overrides)
    return data


def test_settings_normalizes_cookie_samesite():
    settings = Settings(**_settings_kwargs(cookie_samesite="STRICT"))
    assert settings.cookie_samesite == "strict"


def test_settings_rejects_invalid_jwt_algorithm():
    with pytest.raises(ValidationError):
        Settings(**_settings_kwargs(jwt_algorithm="none"))


def test_settings_rejects_invalid_samesite():
    with pytest.raises(ValidationError):
        Settings(**_settings_kwargs(cookie_samesite="invalid"))


def test_settings_ignores_extra_fields():
    settings = Settings.model_validate({**_settings_kwargs(), "extra_field": "ignored"})
    assert settings.app_name == "Maplux"


def test_age_on_boundary():
    today = date(2026, 9, 7)
    assert _age_on(date(2008, 9, 7), today) == 18
    assert _age_on(date(2008, 9, 8), today) == 17


def test_user_create_schema_requires_adult():
    with pytest.raises(ValidationError):
        UserCreateSchema(
            email="kid@example.com",
            first_name="Kid",
            last_name="User",
            date_of_birth=date.today() - timedelta(days=365 * 10),
            phone_number="+1234567890",
            password="Password123",
        )


def test_user_update_schema_allows_null_date_of_birth():
    assert UserUpdateSchema(date_of_birth=None).date_of_birth is None


def test_confirmation_token_enum():
    assert ConfirmationTokenType.ACCOUNT_ACTIVATION.value == "ACCOUNT_ACTIVATION"
    assert ConfirmationTokenType.PASSWORD_RESET.value == "PASSWORD_RESET"
