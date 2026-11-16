from unittest.mock import patch

import pytest
import sqlalchemy
import sqlalchemy.dialects.postgresql as postgresql
from sqlalchemy import JSON, TypeDecorator, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class SQLiteARRAY(TypeDecorator):
    impl = JSON
    cache_ok = True


# Must run before the app models are imported.
sqlalchemy.ARRAY = SQLiteARRAY
postgresql.ARRAY = SQLiteARRAY

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.database import Base, get_db  # noqa: E402
from backend.app.main import app  # noqa: E402

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def db_setup():
    Base.metadata.create_all(bind=engine)
    with patch("backend.app.services.orchestrator.SessionLocal", TestingSessionLocal):
        yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
