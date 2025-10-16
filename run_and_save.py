import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Ensure SQLAlchemy uses the supported dialect name: convert `postgres://` to `postgresql://`
_pg = os.environ.get("POSTGRES_URL")
if _pg and _pg.startswith("postgres://"):
    os.environ["POSTGRES_URL"] = "postgresql://" + _pg[len("postgres://"):]


def run_sync_or_async(fn, *args, **kwargs):
    """Run either a sync or async function and return the result."""
    if asyncio.iscoroutinefunction(fn):
        return asyncio.run(fn(*args, **kwargs))
    return fn(*args, **kwargs)


def try_save_with_crud(items):
    """Try to save items using functions in app.crud if available."""
    try:
        import app.crud as crud
    except Exception:
        return False

    # Look for common upsert functions
    for name in ("upsert_listings", "upsert_many", "upsert_listing", "bulk_upsert", "save_items"):
        fn = getattr(crud, name, None)
        if fn and callable(fn):
            try:
                fn(items)
                print(f"Saved {len(items)} items using app.crud.{name}()")
                return True
            except Exception as e:
                print(f"app.crud.{name}() failed: {e}")
                return False
    return False


def try_save_with_models(items):
    """Fallback: use SQLAlchemy models + get_db to insert Listing objects."""
    try:
        from app.db import get_db
        from app.models import Listing
    except Exception as e:
        print(f"Couldn't import models/db: {e}")
        return False

    try:
        session = next(get_db())
        objs = []
        for it in items:
            if isinstance(it, dict):
                # Only pass keys that exist on Listing
                objs.append(Listing(**it))
        if not objs:
            print("No dict-like items to insert as models.")
            return False
        session.add_all(objs)
        session.commit()
        print(f"Inserted {len(objs)} Listing objects via SQLAlchemy model.")
        return True
    except Exception as e:
        print(f"Failed to insert using models: {e}")
        return False


if __name__ == "__main__":
    print("Running scraper (as package module 'app.scrape') from project root...")

    try:
        # Import the scraper module as a package to allow relative imports inside
        from app.scrape import scrape_marketplace
    except Exception as e:
        raise SystemExit(f"Failed to import 'app.scrape.scrape_marketplace': {e}")

    print("Running scrape_marketplace()...")
    result = run_sync_or_async(scrape_marketplace)

    if result is None:
        print("Scraper returned None — it may have saved results to DB already.")
        raise SystemExit(0)

    if not isinstance(result, (list, tuple)):
        items = [result]
    else:
        items = list(result)

    print(f"Scraper returned {len(items)} item(s). Attempting to save to DB...")

    if try_save_with_crud(items):
        raise SystemExit(0)

    if try_save_with_models(items):
        raise SystemExit(0)

    print("No automatic saver found. Print a single sample item below so you can paste it to me:")
    if items:
        import pprint

        pprint.pprint(items[0])

    print("If you want, I can add an explicit upsert implementation — paste one sample item or the contents of app/crud.py and I will extend the runner.")