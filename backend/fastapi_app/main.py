from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import structlog
import uvicorn

from .routers import alerts, incidents, dashboard, chatops, correlation
from .core.database import init_db
from .core.elasticsearch import init_elasticsearch
from .core.config import settings

logger = structlog.get_logger()
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Alert Intelligence Platform")
    await init_db()
    await init_elasticsearch()
    yield
    logger.info("Shutting down Alert Intelligence Platform")

app = FastAPI(
    title="Alert Intelligence Platform",
    description="Production-ready alert ingestion, correlation, and intelligence platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(chatops.router, prefix="/api/v1/chatops", tags=["chatops"])
app.include_router(correlation.router, prefix="/api/v1/correlation", tags=["correlation"])

@app.get("/")
async def root():
    return {"message": "Alert Intelligence Platform API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "alert-intelligence-platform"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
