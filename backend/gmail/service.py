import base64
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from db.models import get_tokens, save_tokens, upsert_emails
from services.text_cleaning import clean_email_text

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
logger = logging.getLogger("email_rag.gmail")


def _client_config() -> Dict:
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")],
        }
    }


def _to_iso(expiry: Optional[datetime]) -> Optional[str]:
    if not expiry:
        return None
    if not expiry.tzinfo:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry.isoformat()


def _from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            # google-auth compares expiry with naive UTC datetime.
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def build_credentials_from_db() -> Optional[Credentials]:
    tokens = get_tokens()
    if not tokens:
        logger.warning("No OAuth tokens found in DB.")
        return None

    credentials = Credentials(
        token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        scopes=GMAIL_SCOPES,
    )
    credentials.expiry = _from_iso(tokens["expiry"])

    if credentials.expired and credentials.refresh_token:
        logger.info("Access token expired. Refreshing token.")
        credentials.refresh(Request())
        save_tokens(credentials.token, credentials.refresh_token, _to_iso(credentials.expiry))
        logger.info("Access token refreshed and saved.")

    return credentials


def _extract_body(payload: Dict) -> str:
    if not payload:
        return ""

    mime_type = payload.get("mimeType", "")
    body_data = (payload.get("body") or {}).get("data")
    parts = payload.get("parts") or []

    if mime_type == "text/plain" and body_data:
        return _decode_base64(body_data)

    for part in parts:
        part_mime = part.get("mimeType")
        part_data = (part.get("body") or {}).get("data")
        if part_mime == "text/plain" and part_data:
            return _decode_base64(part_data)

    for part in parts:
        nested = _extract_body(part)
        if nested:
            return nested

    if body_data:
        return _decode_base64(body_data)
    return ""


def _decode_base64(content: str) -> str:
    if not content:
        return ""
    padding = "=" * (-len(content) % 4)
    try:
        decoded = base64.urlsafe_b64decode(content + padding)
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _header(headers: List[Dict], key: str) -> str:
    key_lower = key.lower()
    for item in headers:
        if item.get("name", "").lower() == key_lower:
            return item.get("value", "")
    return ""


def sync_last_100_emails(credentials: Optional[Credentials] = None) -> int:
    creds = credentials or build_credentials_from_db()
    if not creds:
        logger.warning("Gmail sync skipped: no valid credentials.")
        return 0

    logger.info("Starting Gmail sync for last 100 emails.")
    service = build("gmail", "v1", credentials=creds)
    response = service.users().messages().list(userId="me", maxResults=100).execute()
    messages = response.get("messages", [])
    logger.info("Fetched message IDs from Gmail. count=%s", len(messages))
    normalized = []

    for message_meta in messages:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_meta["id"], format="full")
            .execute()
        )
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        subject = _header(headers, "Subject")
        sender = _header(headers, "From")
        date = _header(headers, "Date")
        snippet = message.get("snippet", "")
        body = clean_email_text(_extract_body(payload))
        normalized.append(
            {
                "id": message.get("id", ""),
                "thread_id": message.get("threadId", ""),
                "subject": subject,
                "sender": sender,
                "body": body,
                "snippet": snippet,
                "date": date,
            }
        )

    upsert_emails(normalized)
    logger.info("Upserted emails into SQLite. count=%s", len(normalized))
    return len(normalized)


def oauth_client_config() -> Dict:
    return _client_config()
