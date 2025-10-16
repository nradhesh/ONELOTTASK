# app/services.py
from . import crud, schemas
from sqlalchemy.orm import Session
from .utils import logger
from typing import Dict

def ingest_listing(db: Session, payload: Dict):
    # Basic normalization/validation
    if "listing_id" not in payload:
        raise ValueError("listing_id missing")
    # Optional: sanitize numeric fields
    if payload.get("price") is not None:
        try:
            payload["price"] = float(payload["price"])
        except:
            payload["price"] = None
    crud.upsert_listing(db, payload)
    logger.info("Ingested listing %s", payload["listing_id"])
    return payload["listing_id"]
