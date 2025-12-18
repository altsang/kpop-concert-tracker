"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1 import api_router
from app.config import get_settings
from app.database import create_db_and_tables

settings = get_settings()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await create_db_and_tables()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    description="Track K-pop concert announcements from Twitter",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=TEMPLATES_DIR) if TEMPLATES_DIR.exists() else None

# Include API routes
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard page."""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(
        content="""
        <html>
            <head><title>K-Pop Concert Tracker</title></head>
            <body>
                <h1>K-Pop Concert Tracker</h1>
                <p>Dashboard templates not found. API is available at <a href="/docs">/docs</a></p>
            </body>
        </html>
        """
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
