from fastapi import FastAPI
from app.db import Base, engine
import app.models  # noqa: F401 ensure models are imported so tables are known

# create FastAPI instance
app = FastAPI()

# try to include API routes if available
try:
    from app.api.routes import router as api_router
    app.include_router(api_router)
except Exception:
    # routes not available or import failed; keep app running
    pass

# import scheduler to start background tasks if the module starts them on import
try:
    import app.scheduler  # noqa: F401
except Exception:
    pass


@app.on_event("startup")
def on_startup_create_tables():
    # Ensure database tables are created on startup
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        # Do not crash the app if migrations are preferred; keep running
        pass