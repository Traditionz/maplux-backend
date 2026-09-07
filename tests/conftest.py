import os

os.environ["TESTING"] = "true"

from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from domain.user import repository as user_repository
from domain.user.schemas import UserCreateInternalSchema
from main import app
from security.authentication import create_access_token, hash_password
from utils.ids import generate_id

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db() -> Generator[Session]:
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client(db: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_email(monkeypatch: pytest.MonkeyPatch):
    class FakeEmail:
        instances: list = []

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            FakeEmail.instances.append(self)

        async def send_activation_email(self) -> None:
            return None

        async def send_password_reset_email(self) -> None:
            return None

    FakeEmail.instances = []
    monkeypatch.setattr("routers.user_router.Email", FakeEmail)
    return FakeEmail


def make_user(
    db: Session,
    *,
    email: str = "jane@example.com",
    password: str = "Password123",
    activated: bool = True,
    is_admin: bool = False,
    first_name: str = "Jane",
    last_name: str = "Doe",
):
    password_salt, password_hashed = hash_password(password)
    return user_repository.create_user(
        db,
        UserCreateInternalSchema(
            user_id=generate_id(),
            email=email,
            activated=activated,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date(1990, 1, 1),
            phone_number="+1234567890",
            password_salt=password_salt,
            password_hashed=password_hashed,
            is_admin=is_admin,
        ),
    )


def auth_header(email: str) -> dict[str, str]:
    token = create_access_token({"sub": email})
    return {"Authorization": f"Bearer {token}"}


VALID_USER_PAYLOAD = {
    "email": "john@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "dateOfBirth": "1990-01-01",
    "phoneNumber": "+1234567890",
    "password": "Test1234",
}

ADDRESS_PAYLOAD = {
    "streetAddress": "123 Main St",
    "aptSuite": "4B",
    "city": "Austin",
    "stateProvince": "TX",
    "postalZip": "78701",
    "country": "US",
}
