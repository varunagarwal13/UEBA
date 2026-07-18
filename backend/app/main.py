"""
main.py
-------
The application entry point.
- Creates all DB tables on startup
- Registers all routers
- Runs with uvicorn
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import logs, alerts, risk, dashboard, users, simulator
import os

# Create all tables defined in models.py
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title       = "Anomaly Detection Backend — MVP",
    description = "Backend API for CTMC-based user behavior anomaly detection (BFSI)",
    version     = "1.0.0",
)

# CORS — allow Person 3's frontend (React/Next.js) to call these APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # tighten this for production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Register all routers
app.include_router(logs.router)
app.include_router(alerts.router)
app.include_router(risk.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(simulator.router)

# Mount static frontend files
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out"))
if not os.path.exists(frontend_dir):
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}