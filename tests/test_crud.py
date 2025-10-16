# tests/test_crud.py
import pytest
from app import crud, models
from app.db import Base, engine, SessionLocal

@pytest.fixture(scope="module")
def db():
    # use a test DB or the same DB with a test schema
    conn = engine.connect()
    trans = conn.begin()
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    trans.rollback()
    conn.close()

def test_upsert_and_get(db):
    payload = {"listing_id": "test123", "title": "Test Car", "price": 1000, "url":"http://x"}
    crud.upsert_listing(db, payload)
    obj = crud.get_listing(db, "test123")
    assert obj is not None
    assert obj.title == "Test Car"
