from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import get_secret_key
from app.database import Base, engine
from app.routes.auth import router as auth_router
from app.routes.notes import router as notes_router

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_secret_key()
    Base.metadata.create_all(bind=engine)
    # SQLite cannot add a foreign key constraint to an existing table in place.
    # Preserve legacy notes as unowned instead of deleting or exposing them.
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(notes)")}
        if "user_id" not in columns:
            connection.exec_driver_sql("ALTER TABLE notes ADD COLUMN user_id INTEGER")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notes_user_id ON notes (user_id)")
    yield


app = FastAPI(title="Cloud Notes", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(notes_router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
