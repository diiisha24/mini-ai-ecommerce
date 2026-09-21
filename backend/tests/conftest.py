import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.main import app
from app.models import Product, Role, User
from app.security import create_access_token


@pytest.fixture()
def session():
    # In-memory SQLite, single shared connection so both the test setup and the
    # app's requests (via dependency override below) see the same data.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    # No `with` block: this intentionally skips the app's lifespan (which would try
    # to `init_db()` against the real configured Postgres URL) - tests only need the
    # SQLite session above, already created.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(session):
    def _make(email: str, role: Role = Role.customer) -> User:
        user = User(google_sub=f"sub-{email}", email=email, name=email, role=role)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    return _make


@pytest.fixture()
def auth_headers():
    def _headers(user: User) -> dict:
        token = create_access_token(user_id=user.id, role=user.role.value)
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture()
def make_product(session):
    def _make(**kwargs) -> Product:
        defaults = {"name": "Test Product", "description": "", "price": 10, "stock": 5}
        defaults.update(kwargs)
        product = Product(**defaults)
        session.add(product)
        session.commit()
        session.refresh(product)
        return product

    return _make
