from __future__ import annotations

import re
from collections import Counter


URL_PATTERN = re.compile(r"https?://[^\s>]+")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_ぁ-んァ-ヶ一-龠]{2,}")

STOPWORDS = {
    "こと", "これ", "それ", "ため", "よう", "もの", "感じ", "記事", "自分", "今日", "今週",
    "です", "ます", "する", "した", "して", "ある", "いる", "なる", "その", "から", "まで",
    "with", "from", "this", "that", "have", "been", "into", "about", "https", "http",
}


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def extract_urls(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0).rstrip(").,") for match in URL_PATTERN.finditer(text)))


def top_keywords(texts: list[str], limit: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        for token in TOKEN_PATTERN.findall(normalize_text(text)):
            if token not in STOPWORDS and not token.isdigit():
                counter[token] += 1
    return [word for word, _count in counter.most_common(limit)]
