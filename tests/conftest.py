import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from helpmeet_licenses.database import Base, get_db
from helpmeet_licenses.main import app

TEST_DB = "sqlite:///./test.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def a_license(db):
    """Crea un customer + licencia activa en la DB de test."""
    from helpmeet_licenses.models import Customer, License
    from helpmeet_licenses.auth import hash_key
    from datetime import date
    key = "HM-TEST-1234-ABCD-5678"
    customer = Customer(email="test@test.com", name="Test User")
    db.add(customer)
    db.flush()
    lic = License(
        customer_id=customer.id,
        key_hash=hash_key(key),
        key_last4=key[-4:],
        plan="personal",
        status="active",
        updates_until=date(2027, 6, 28),
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return {"license": lic, "key": key}
