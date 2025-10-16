# app/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas
from ..db import get_db
from ..scrape import scrape_marketplace
from ..utils import logger

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/listings", response_model=List[schemas.ListingOut])
def listings(
    skip: int = 0,
    limit: int = 20,
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    min_year: int | None = Query(None),
    max_year: int | None = Query(None),
    location: str | None = Query(None),
    db: Session = Depends(get_db)
):
    filters = {
        "min_price": min_price,
        "max_price": max_price,
        "min_year": min_year,
        "max_year": max_year,
        "location": location
    }
    res = crud.list_listings(db, skip=skip, limit=limit, filters=filters)
    return res["items"]


@router.get("/listings/{listing_id}", response_model=schemas.ListingOut)
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    obj = crud.get_listing(db, listing_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Listing not found")
    return obj


@router.patch("/listings/{listing_id}", response_model=schemas.ListingOut)
def update_listing(listing_id: str, payload: schemas.ListingUpdate, db: Session = Depends(get_db)):
    obj = crud.update_listing(db, listing_id, updates=payload.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Listing not found")
    return obj


@router.delete("/listings/{listing_id}")
def delete_listing(listing_id: str, db: Session = Depends(get_db)):
    ok = crud.delete_listing(db, listing_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"status": "deleted"}

@router.post("/scrape")
def trigger_scrape():
    try:
        scrape_marketplace()
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Scrape failed: %s", e)
        raise HTTPException(status_code=500, detail="Scrape failed")
