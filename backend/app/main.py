# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.api.routes import document_routes, websocket_routes, project_routes, ai_routes, baw_routes
from app.core.settings import settings
from app.services.ai_service import lifespan
from app.core.logging_config import setup_logging
import logging

# Setup logging first with mode from settings
setup_logging(mode=settings.LOGGING_MODE)
logger = logging.getLogger(__name__)
logger.info("Application starting...")
logger.info(f"Logging mode: {settings.LOGGING_MODE}")

# Create FastAPI app with lifespan for agent initialization
app = FastAPI(
    title="AI Application API",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Root route to serve index.html
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(Path(__file__).parent / "static" / "index.html") as f:
        return HTMLResponse(content=f.read())

# Include routers
app.include_router(ai_routes.router, prefix="/api/v1", tags=["AI"])
app.include_router(project_routes.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(document_routes.router, prefix="/api/v1", tags=["Documents"])
app.include_router(websocket_routes.router, tags=["WebSocket"])
app.include_router(baw_routes.router, prefix="/api/v1", tags=["BAW"])

