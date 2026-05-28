"""Omics Copilot — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import chat, data, files, pipeline, projects, settings, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .services.project_store import init_db
    await init_db()
    yield


app = FastAPI(
    title="Omics Copilot",
    version="0.1.0",
    description="AI-powered multi-omics analysis platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",  # Vite preview
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
