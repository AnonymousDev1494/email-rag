import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional

from rank_bm25 import BM25Okapi

from db.models import get_all_emails
from services.text_cleaning import preprocess_for_bm25


def _extract_sender_hint(question: str) -> Optional[str]:
    patterns = [
        r"(?:from|sent by|email by|emails by)\s+([a-zA-Z0-9._%+\- ]{2,80})",
    ]
    for pattern in patterns:
        match = re.search(pattern, question.lower())
        if match:
            candidate = match.group(1).strip(" .,!?:;\"'")
            if candidate:
                return candidate
    return None


def _extract_time_window(question: str) -> Optional[int]:
    lowered = question.lower()
    if "today" in lowered:
        return 1
    if "yesterday" in lowered:
        return 2
    if "last week" in lowered or "this week" in lowered:
        return 7
    if "last month" in lowered or "this month" in lowered:
        return 30
    return None


def _parse_email_date(date_text: str) -> Optional[datetime]:
    if not date_text:
        return None
    try:
        parsed = parsedate_to_datetime(date_text)
        if parsed and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _filter_by_sender_hint(emails: List[Dict], question: str) -> List[Dict]:
    sender_hint = _extract_sender_hint(question)
    if not sender_hint:
        return emails
    hint_tokens = set(preprocess_for_bm25(sender_hint))
    if not hint_tokens:
        return emails

    filtered = []
    for email in emails:
        sender_text = (email.get("sender") or "").lower()
        sender_tokens = set(preprocess_for_bm25(sender_text))
        if sender_hint in sender_text or hint_tokens.issubset(sender_tokens):
            filtered.append(email)
    return filtered if filtered else emails


def _filter_by_time_window(emails: List[Dict], question: str) -> List[Dict]:
    days = _extract_time_window(question)
    if not days:
        return emails
    now = datetime.now(timezone.utc)
    filtered = []
    for email in emails:
        parsed = _parse_email_date(email.get("date", ""))
        if parsed and (now - parsed).days <= days:
            filtered.append(email)
    return filtered if filtered else emails


def _apply_metadata_filters(emails: List[Dict], question: str) -> List[Dict]:
    sender_filtered = _filter_by_sender_hint(emails, question)
    return _filter_by_time_window(sender_filtered, question)


def _recency_boost(date_text: str) -> float:
    if not date_text:
        return 0.0
    parsed = _parse_email_date(date_text)
    if parsed is None:
        return 0.0
    now = datetime.now(timezone.utc)
    age_days = max((now - parsed).days, 0)
    # Fresh emails get a stronger boost while old emails decay smoothly.
    return 1.0 / (1.0 + (age_days / 14.0))


def _expand_by_threads(ranked: List[Dict], all_emails: List[Dict], max_emails: int = 20) -> List[Dict]:
    if not ranked:
        return []
    by_id = {item.get("id", ""): item for item in all_emails}
    thread_ids = {item.get("thread_id", "") for item in ranked if item.get("thread_id")}
    expanded: List[Dict] = []
    used_ids = set()

    for item in ranked:
        item_id = item.get("id", "")
        if item_id and item_id not in used_ids:
            expanded.append(item)
            used_ids.add(item_id)

    for email in all_emails:
        thread_id = email.get("thread_id", "")
        item_id = email.get("id", "")
        if thread_id in thread_ids and item_id and item_id not in used_ids:
            expanded.append(email)
            used_ids.add(item_id)
        if len(expanded) >= max_emails:
            break

    return expanded[:max_emails]


def retrieve_top_emails(question: str, limit: int = 10) -> List[Dict]:
    all_emails = get_all_emails()
    emails = _apply_metadata_filters(all_emails, question)
    if not emails:
        return []

    corpus = []
    for email in emails:
        combined = " ".join(
            [
                email.get("subject") or "",
                email.get("sender") or "",
                email.get("snippet") or "",
                email.get("body") or "",
            ]
        ).strip()
        corpus.append(preprocess_for_bm25(combined))

    query_tokens = preprocess_for_bm25(question)
    if not query_tokens:
        return []

    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query_tokens)
    indexed_scores = []
    for index, score in enumerate(scores):
        bm25_score = float(score)
        if bm25_score <= 0:
            continue
        recency_score = _recency_boost(emails[index].get("date", ""))
        final_score = bm25_score + (0.35 * recency_score)
        indexed_scores.append((index, final_score, bm25_score, recency_score))
    indexed_scores.sort(key=lambda item: item[1], reverse=True)

    if not indexed_scores:
        # Small filtered corpora can yield zero BM25 scores; keep top items anyway.
        indexed_scores = sorted(
            [
                (
                    index,
                    float(score) + (0.35 * _recency_boost(emails[index].get("date", ""))),
                    float(score),
                    _recency_boost(emails[index].get("date", "")),
                )
                for index, score in enumerate(scores)
            ],
            key=lambda item: item[1],
            reverse=True,
        )[:limit]
        if not indexed_scores:
            return []

    results: List[Dict] = []
    for idx, final_score, bm25_score, recency_score in indexed_scores[:limit]:
        email = emails[idx]
        results.append(
            {
                "id": email["id"],
                "thread_id": email.get("thread_id", ""),
                "subject": email.get("subject", ""),
                "sender": email.get("sender", ""),
                "snippet": email.get("snippet", ""),
                "body": email.get("body", ""),
                "date": email.get("date", ""),
                "score": final_score,
                "bm25_score": bm25_score,
                "recency_boost": recency_score,
            }
        )
    return _expand_by_threads(results, all_emails, max_emails=20)


def pick_top_sources(candidates: List[Dict], selected_ids: List[str], top_k: int = 3) -> List[Dict]:
    if not candidates:
        return []
    if not selected_ids:
        return candidates[:top_k]
    by_id = {item.get("id", ""): item for item in candidates}
    selected = [by_id[item_id] for item_id in selected_ids if item_id in by_id]
    return (selected or candidates[:top_k])[:top_k]


def format_context(top_emails: List[Dict]) -> List[str]:
    context_blocks = []
    for position, email in enumerate(top_emails, start=1):
        body = (email.get("body") or "").strip()
        if len(body) > 2000:
            body = body[:2000] + "..."
        block = (
            f"Email {position}\n"
            f"ID: {email.get('id', '')}\n"
            f"Thread ID: {email.get('thread_id', '')}\n"
            f"Subject: {email.get('subject', '')}\n"
            f"Sender: {email.get('sender', '')}\n"
            f"Date: {email.get('date', '')}\n"
            f"Snippet: {email.get('snippet', '')}\n"
            f"Body:\n{body}"
        )
        context_blocks.append(block)
    return context_blocks
