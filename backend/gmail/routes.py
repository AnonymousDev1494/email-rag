import logging
from threading import Lock

from fastapi import APIRouter, HTTPException

from gmail.service import build_credentials_from_db, sync_last_100_emails

router = APIRouter(prefix="/gmail", tags=["gmail"])
logger = logging.getLogger("email_rag.gmail.routes")
_sync_lock = Lock()


def _sync_emails_impl():
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Email sync already running.")
    try:
        credentials = build_credentials_from_db()
        if not credentials:
            raise HTTPException(status_code=401, detail="Connect Gmail first.")

        count = sync_last_100_emails(credentials=credentials)
        logger.info("Manual Gmail sync completed. emails_saved=%s", count)
        return {"ok": True, "emails_synced": count}
    finally:
        _sync_lock.release()


@router.post("/sync")
def sync_emails():
    return _sync_emails_impl()


emails_router = APIRouter(prefix="/emails", tags=["emails"])


@emails_router.post("/sync")
def sync_emails_alias():
    return _sync_emails_impl()
