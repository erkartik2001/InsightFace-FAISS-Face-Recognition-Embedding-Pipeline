from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routes.indexing_routes import router as indexing_router
from app.routes.matching_routes import router as matching_router

from app.matcher import FaceMatcher
import app.app_state as app_state

from app.services.face_engine import FaceEngine
from app.services.storage_service import B2Storage
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Database
from app.database import engine, Base
from app.models import IndexingState, SchedulerLog

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Create DB tables (idempotent)
    print("=" * 50)
    print("Face Recognition Embedding Pipeline")
    print("=" * 50)

    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)
    print("Database Ready")
    print("-" * 20)

    print("Loading Face Engine")
    app_state.face_engine = FaceEngine()
    print("Face Engine Loaded")
    print("-" * 20)

    print("Loading B2 Storage")
    app_state.b2_storage = B2Storage()
    print("B2 Storage Loaded")
    print("-" * 20)

    print("Loading Face Matcher....")
    app_state.matcher = FaceMatcher()
    print("Matcher loaded successfully")
    print("-" * 20)

    print("Pipeline Service Ready!")
    print("=" * 50)

    yield

    print("Shutting down Pipeline Service...")


app = FastAPI(
    title="Face Recognition Embedding Pipeline",
    description=(
        "Core service for face recognition, embedding generation, "
        "indexing, and face matching. "
        "Used by AI Face Recognition CRM as a backend service."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Allow CRM service to call this service
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "*"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "service": "Face Recognition Embedding Pipeline",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "face_engine": app_state.face_engine is not None,
        "b2_storage": app_state.b2_storage is not None,
        "matcher": app_state.matcher is not None,
        "sync_in_progress": app_state.sync_in_progress,
        "scheduler_running": app_state.scheduler_running,
        "scheduler_status": app_state.scheduler_info["status"]
    }


# Register routes
app.include_router(indexing_router)
app.include_router(matching_router)
