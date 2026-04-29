import logging
from collections import defaultdict, deque
from pydantic import BaseModel
from fastapi import APIRouter

from rag.retriever import format_context, pick_top_sources, retrieve_top_emails
from services.openrouter import FALLBACK_TEXT, answer_from_context, rerank_email_ids, rewrite_query

router = APIRouter(prefix="/rag", tags=["rag"])
logger = logging.getLogger("email_rag.rag")
_session_memory = defaultdict(lambda: deque(maxlen=6))


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None


def _build_sources(top_emails):
    return [
        {
            "id": item.get("id", ""),
            "subject": item.get("subject", ""),
            "sender": item.get("sender", ""),
            "date": item.get("date", ""),
            "score": round(float(item.get("score", 0.0)), 3),
        }
        for item in top_emails[:3]
    ]


@router.post("/query")
def rag_query(payload: QueryRequest):
    question = (payload.question or "").strip()
    session_id = (payload.session_id or "default").strip() or "default"
    logger.info("RAG query received. question_len=%s", len(question))
    if not question:
        logger.info("RAG fallback: empty question.")
        return {"answer": FALLBACK_TEXT, "sources": []}

    rewritten_query = rewrite_query(question)
    logger.info("Rewritten query=%s", rewritten_query)

    candidates = retrieve_top_emails(rewritten_query, limit=10)
    if not candidates:
        logger.info("RAG fallback: no BM25 matches.")
        return {"answer": FALLBACK_TEXT, "sources": []}
    logger.info(
        "Retrieval candidates found. count=%s top_score=%.3f",
        len(candidates),
        float(candidates[0].get("score", 0.0)),
    )

    selected_ids = rerank_email_ids(question, candidates, top_k=3)
    top_emails = pick_top_sources(candidates, selected_ids, top_k=3)
    logger.info("Rerank selected. selected_count=%s", len(top_emails))

    history_items = list(_session_memory[session_id])[-3:]
    history_blocks = [f"{item['role']}: {item['content']}" for item in history_items]
    context_blocks = format_context(top_emails)
    answer = answer_from_context(question, context_blocks, history_blocks)
    if not answer or not answer.strip():
        logger.info("RAG fallback: empty LLM response.")
        answer = FALLBACK_TEXT

    _session_memory[session_id].append({"role": "user", "content": question})
    _session_memory[session_id].append({"role": "assistant", "content": answer.strip()})

    logger.info("RAG response ready. is_fallback=%s", answer.strip() == FALLBACK_TEXT)
    return {"answer": answer.strip(), "sources": _build_sources(top_emails)}
