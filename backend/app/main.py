"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.api.v1 import auth, learning, analytics, resumes, coding, sql_lab, diagrams, bookmarks, revision, projects, discover

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Interview Academy API starting up", version=settings.VERSION)
    yield
    logger.info("Interview Academy API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Personalized technical learning platform for Nawin Asokan — Python Backend Developer",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(learning.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(resumes.router, prefix=API_PREFIX)
app.include_router(coding.router, prefix=API_PREFIX)
app.include_router(sql_lab.router, prefix=API_PREFIX)
app.include_router(diagrams.router, prefix=API_PREFIX)
app.include_router(bookmarks.router, prefix=API_PREFIX)
app.include_router(revision.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(discover.router, prefix=API_PREFIX)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "tagline": "Master Backend Development. Understand Every Concept. Build Real-World Skills.",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.VERSION}
