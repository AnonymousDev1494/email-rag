import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.routes import router as auth_router
from db.database import init_db
from db.models import get_email_count, get_tokens
from gmail.routes import emails_router, router as gmail_router
from rag.routes import router as rag_router

load_dotenv()
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("email_rag.main")

app = FastAPI(title="Gmail BM25 RAG Assistant")

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    logger.info("Startup complete. DB initialized at %s", os.getenv("DATABASE_PATH", "./email_rag.db"))


@app.get("/health")
def health():
    connected = bool(get_tokens())
    cached = get_email_count()
    logger.info("Health check: connected=%s emails_cached=%s", connected, cached)
    return {
        "ok": True,
        "connected": connected,
        "emails_cached": cached,
    }


app.include_router(auth_router)
app.include_router(gmail_router)
app.include_router(emails_router)
app.include_router(rag_router)
