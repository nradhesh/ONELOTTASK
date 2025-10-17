# app/models.py
"""SQLAlchemy ORM models for persisted entities.

Currently defines the `Listing` model and related indexes. This documentation
does not change runtime logic.
"""
from sqlalchemy import Column, Integer, Text, Numeric, TIMESTAMP, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from .db import Base

class Listing(Base):
    __tablename__ = "listings"
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Text, nullable=False, unique=True, index=True)
    title = Column(Text)
    price = Column(Numeric)
    currency = Column(Text)
    year = Column(Integer)
    mileage = Column(Integer)
    location = Column(Text)
    url = Column(Text)
    raw_json = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

Index("idx_listings_price", Listing.price)
Index("idx_listings_year", Listing.year)
