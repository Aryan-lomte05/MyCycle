"""MyCycle FastAPI Backend Application.

Provides privacy-preserving content, reminder rules, and aggregate metric recording.
Does not store, receive, or log individual cycle or symptom details.
Privacy policy: Your cycle logs stay on your phone. You choose what to share.
"""
from __future__ import annotations

import importlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.db import init_db
from server.routes.content import router as content_router
from server.routes.metrics import router as metrics_router
from server.routes.reminders import router as reminders_router

app = FastAPI(
    title="MyCycle Backend API",
    version="1.0.0",
    description="Privacy-preserving menstrual health screening platform: education content, reminder rules, and aggregate metrics. Your cycle logs stay on your phone. You choose what to share."
)

# CORS configuration for local prototype and PWA integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize local SQLite database (PostgreSQL production migration: planned, not yet done)
init_db()


@app.get("/v1/health", tags=["system"])
def health_check():
    """Health check endpoint confirming API service status."""
    return {
        "status": "ok",
        "app": "MyCycle",
        "version": "1.0.0",
        "privacy": "Your cycle logs stay on your phone. You choose what to share.",
        "database": "SQLite local development (PostgreSQL migration: planned, not yet done)",
        "family_sharing": "planned, not yet done (owned by Liza in routes/family.py)"
    }


# Include core routers under /v1
app.include_router(content_router, prefix="/v1")
app.include_router(reminders_router, prefix="/v1")
app.include_router(metrics_router, prefix="/v1")

# Mount family router if present (owned by Liza, do not modify routes/family.py)
try:
    family_module = importlib.import_module("server.routes.family")
    if hasattr(family_module, "router"):
        app.include_router(family_module.router, prefix="/v1")
except ImportError:
    pass
