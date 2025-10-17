# app/crud.py
"""CRUD operations for `Listing` entities.

This module provides create, read, update, and delete helpers as well as
an idempotent upsert utility. Edits here are documentation-only and do not
affect runtime behavior.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select, and_, func
from .models import Listing
from sqlalchemy.orm import Session
from typing import Dict, Any, List

def upsert_listing(db: Session, data: Dict[str, Any]):
    table = Listing.__table__
    stmt = pg_insert(table).values(**data)
    # copy all updatable columns from EXCLUDED, but override timestamps
    excluded = {c.name: stmt.excluded[c.name] for c in table.columns if c.name not in ("id", "created_at")}
    # ensure refresh semantics on re-run
    excluded["updated_at"] = func.now()
    excluded["last_seen_at"] = func.now()
    stmt = stmt.on_conflict_do_update(index_elements=['listing_id'], set_=excluded)
    db.execute(stmt)
    db.commit()

def get_listing(db: Session, listing_id: str):
    return db.query(Listing).filter(Listing.listing_id == listing_id).first()

def list_listings(db: Session, skip: int = 0, limit: int = 50, filters: Dict = None):
    q = db.query(Listing)
    if filters:
        conds = []
        if filters.get("min_price") is not None:
            conds.append(Listing.price >= filters["min_price"])
        if filters.get("max_price") is not None:
            conds.append(Listing.price <= filters["max_price"])
        if filters.get("min_year") is not None:
            conds.append(Listing.year >= filters["min_year"])
        if filters.get("max_year") is not None:
            conds.append(Listing.year <= filters["max_year"])
        if filters.get("location"):
            conds.append(Listing.location.ilike(f"%{filters['location']}%"))
        if conds:
            q = q.filter(and_(*conds))
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return {"total": total, "items": items}

def update_listing(db: Session, listing_id: str, updates: Dict[str, Any]):
    obj = db.query(Listing).filter(Listing.listing_id == listing_id).first()
    if not obj:
        return None
    for k, v in updates.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_listing(db: Session, listing_id: str):
    obj = db.query(Listing).filter(Listing.listing_id == listing_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
