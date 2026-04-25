"""
main.py — LexAI Backend Entry Point
=====================================
Run with:
    uvicorn main:app --reload --port 8000

Architecture:
    Frontend (HTML/JS)
        ↓  HTTP  →  Backend (FastAPI)
        ↓              ↓
        ↓         AgentOrchestrator
        ↓       ↙    ↓    ↓       ↘
        ↓  Research Defense Prosecution Judge → Appeals
        ↓              ↓
        ↓          Anthropic LLM
        ↓
      SQLite DB  (case history)
      JWT Auth   (user sessions)
      Rate Limit (10 req/min per IP on /analyze)
      Logging    (loguru — console + files)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import router as main_router
from auth.routes import router as auth_router
from db.database import init_db
from middleware.rate_limit import RateLimitExceeded, limiter, rate_limit_handler
from middleware.logging_middleware import LoggingMiddleware
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LexAI backend starting up…")
    await init_db()
    logger.info("Database tables initialised.")
    yield
    logger.info("LexAI backend shutting down.")


app = FastAPI(
    title="LexAI — Multi-Agent Legal Reasoning API",
    description="Backend orchestrating Research, Defense, Prosecution, Judge, and Appeals agents.",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Rate Limiting ──────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# ── CORS (tighten origins in production) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:5500", "http://localhost:5500", "*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# ── Request / Response Logging ────────────────────────
app.add_middleware(LoggingMiddleware)

# ── Routers ────────────────────────────────────────────
app.include_router(auth_router)   # /auth/register, /auth/login, /auth/me
app.include_router(main_router)   # /health, /analyze, /analyze/stream, /cases, /cases/{id}/pdf
app.mount("/app", StaticFiles(directory=".", html=True), name="app")


if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
