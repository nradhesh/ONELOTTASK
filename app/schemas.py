# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ListingBase(BaseModel):
    listing_id: str = Field(..., max_length=255)
    title: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    year: Optional[int]
    mileage: Optional[int]
    location: Optional[str]
    url: Optional[str]

class ListingCreate(ListingBase):
    raw_json: Optional[dict]

class ListingUpdate(BaseModel):
    title: Optional[str]
    price: Optional[float]
    year: Optional[int]
    mileage: Optional[int]
    location: Optional[str]

class ListingOut(ListingBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    class Config:
        orm_mode = True

class ListingFilter(BaseModel):
    min_price: Optional[float]
    max_price: Optional[float]
    min_year: Optional[int]
    max_year: Optional[int]
    location: Optional[str]
