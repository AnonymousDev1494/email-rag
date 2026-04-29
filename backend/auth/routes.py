import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from db.models import save_tokens
from gmail.service import GMAIL_SCOPES, oauth_client_config, sync_last_100_emails

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("email_rag.auth")

_oauth_state = None
_oauth_flow = None


def _flow(state: str = None) -> Flow:
    flow = Flow.from_client_config(
        oauth_client_config(),
        scopes=GMAIL_SCOPES,
        state=state,
    )
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    return flow


@router.get("/google")
def auth_google() -> RedirectResponse:
    global _oauth_state, _oauth_flow

    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        logger.error("OAuth start failed: Google client credentials missing.")
        raise HTTPException(status_code=500, detail="Google OAuth credentials are missing.")

    flow = _flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    _oauth_state = state
    _oauth_flow = flow
    logger.info("OAuth start success. state=%s", state)
    return RedirectResponse(authorization_url)


@router.get("/callback")
def auth_callback(code: str, state: str = None) -> RedirectResponse:
    global _oauth_state, _oauth_flow

    if not code:
        logger.warning("OAuth callback missing code.")
        raise HTTPException(status_code=400, detail="Missing authorization code.")
    if _oauth_state and state != _oauth_state:
        logger.warning("OAuth callback invalid state. expected=%s got=%s", _oauth_state, state)
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    flow = _oauth_flow if _oauth_flow is not None else _flow(state=state)
    logger.info("OAuth callback received. Exchanging code for token.")
    flow.fetch_token(code=code)
    credentials = flow.credentials
    expiry = credentials.expiry
    if expiry and not expiry.tzinfo:
        expiry = expiry.replace(tzinfo=timezone.utc)

    save_tokens(
        credentials.token,
        credentials.refresh_token,
        expiry.isoformat() if isinstance(expiry, datetime) else None,
    )
    logger.info("OAuth tokens saved. refresh_token_present=%s", bool(credentials.refresh_token))

    count = sync_last_100_emails(credentials=credentials)
    logger.info("Gmail sync completed from callback. emails_saved=%s", count)
    _oauth_state = None
    _oauth_flow = None

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    logger.info("OAuth callback redirecting to frontend chat.")
    return RedirectResponse(f"{frontend_url}/chat?connected=1")
