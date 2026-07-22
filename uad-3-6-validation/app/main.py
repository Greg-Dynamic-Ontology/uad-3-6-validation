from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITE_DIRECTORY = PROJECT_ROOT / "site"

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(router)
app.mount(
    "/",
    StaticFiles(directory=SITE_DIRECTORY, html=True),
    name="site",
)
