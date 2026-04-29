import os
import logging
import json
import re
from typing import Dict, List

import requests


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FALLBACK_TEXT = "Not found in your emails."
FALLBACK_MODELS = [
    "deepseek/deepseek-r1-0528:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "meta-llama/llama-3.3-8b-instruct:free",
]
logger = logging.getLogger("email_rag.openrouter")


def build_prompt(emails_context: str, history_text: str, question: str) -> str:
    return f"""You are an AI assistant that answers ONLY from the provided email context.

Rules:

* ONLY use the given emails
* DO NOT use external knowledge
* DO NOT guess
* If answer is not clearly present, respond EXACTLY:
  Not found in your emails.

Context:
{emails_context}

Conversation History:
{history_text}

Question:
{question}

Answer:"""


def _call_openrouter(prompt: str, temperature: float = 0) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        logger.warning("OpenRouter call skipped: API key not configured.")
        return ""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    configured_model = os.getenv("OPENROUTER_MODEL", "").strip()
    models_to_try = [configured_model] if configured_model else []
    models_to_try.extend(model for model in FALLBACK_MODELS if model and model not in models_to_try)

    content = ""
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        try:
            logger.info("OpenRouter request attempt. model=%s", model)
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            if content:
                logger.info("OpenRouter success. model=%s", model)
                break
        except Exception as exc:
            logger.warning("OpenRouter request failed. model=%s error=%s", model, str(exc))
            continue

    if not content:
        logger.info("OpenRouter fallback: no valid model response.")
        return ""

    return content.strip()


def rewrite_query(question: str) -> str:
    prompt = f"""Rewrite this question into a short search query for email retrieval.
Return only keywords, no sentence.

Question: {question}
Rewritten query:"""
    rewritten = _call_openrouter(prompt, temperature=0)
    if not rewritten:
        return question
    cleaned = re.sub(r"\s+", " ", rewritten).strip()
    return cleaned or question


def rerank_email_ids(question: str, candidates: List[Dict], top_k: int = 3) -> List[str]:
    if not candidates:
        return []
    serialized = []
    for item in candidates[:10]:
        serialized.append(
            {
                "id": item.get("id", ""),
                "thread_id": item.get("thread_id", ""),
                "subject": item.get("subject", ""),
                "sender": item.get("sender", ""),
                "snippet": (item.get("snippet", "") or "")[:240],
                "date": item.get("date", ""),
            }
        )

    prompt = (
        "Select the most relevant email IDs for the question.\n"
        f"Return STRICT JSON array of up to {top_k} ids only, e.g. [\"id1\",\"id2\"].\n\n"
        f"Question: {question}\n"
        f"Candidates: {json.dumps(serialized)}\n"
        "IDs:"
    )
    raw = _call_openrouter(prompt, temperature=0)
    if not raw:
        return []
    try:
        ids = json.loads(raw)
        if isinstance(ids, list):
            cleaned = [str(item) for item in ids if str(item).strip()]
            return cleaned[:top_k]
    except Exception:
        pass
    return []


def answer_from_context(question: str, context_blocks: List[str], history_blocks: List[str]) -> str:
    prompt = build_prompt("\n\n".join(context_blocks), "\n".join(history_blocks), question)
    content = _call_openrouter(prompt, temperature=0)
    if not content:
        return FALLBACK_TEXT

    lowered = content.strip().lower()
    if "not found in your emails" in lowered:
        logger.info("OpenRouter returned fallback phrase.")
        return FALLBACK_TEXT
    return content.strip()


def query_openrouter(question: str, context_blocks: List[str]) -> str:
    return answer_from_context(question, context_blocks, [])
