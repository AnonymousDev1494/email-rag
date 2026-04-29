import re
from html import unescape
from typing import List


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
    "you",
    "your",
    "i",
    "we",
    "they",
    "this",
    "those",
    "these",
}


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return unescape(text)


def strip_quoted_reply(text: str) -> str:
    if not text:
        return ""

    lines = []
    for line in text.splitlines():
        if line.strip().startswith(">"):
            continue
        if re.match(r"^On .+wrote:$", line.strip()):
            break
        lines.append(line)
    return "\n".join(lines)


def clean_email_text(text: str) -> str:
    text = strip_html(text)
    text = strip_quoted_reply(text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def preprocess_for_bm25(text: str) -> List[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [token for token in text.split() if token and token not in STOPWORDS]
    return tokens
