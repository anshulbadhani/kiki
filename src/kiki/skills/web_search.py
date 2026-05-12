"""
Skill: web_search
Search the web and return a concise summary via Groq.
Requires network. Uses Groq with the fast 8b model to summarise results.
"""
from __future__ import annotations
import urllib.request
import urllib.parse
import json
import re

from ..config import GROQ_API_KEY, KIKI_NAME

NAME        = "web_search"
DESCRIPTION = "search find look up browse information on the web internet google"
EXAMPLES    = [
    "search for python tutorials",
    "find me a pasta recipe",
    "look up the news today",
    "what is the weather in delhi",
    "google machine learning",
    "find information about black holes",
    "search the web for kiki",
    "look up how to use git",
    "find me information about",
    "what is happening in the world",
]
PARAMETERS      = {"query": "full user message"}
REQUIRES_VISION = False

# use the smallest fastest groq model for search summarisation
_SEARCH_MODEL = "llama-3.1-8b-instant"
_MAX_TOKENS   = 200

# ---------------------------------------------------------------------------
# DuckDuckGo instant answer — zero API key, no scraping
# ---------------------------------------------------------------------------

def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Hits DuckDuckGo's unofficial JSON endpoint.
    Returns list of {title, snippet, url}.
    """
    encoded = urllib.parse.quote(query)
    url     = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&no_html=1"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "kiki-ai/0.1"}
    )

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        raise RuntimeError(f"search request failed: {e}")

    results = []

    # abstract (direct answer)
    if data.get("AbstractText"):
        results.append({
            "title":   data.get("Heading", ""),
            "snippet": data["AbstractText"],
            "url":     data.get("AbstractURL", ""),
        })

    # related topics
    for topic in data.get("RelatedTopics", [])[:max_results]:
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({
                "title":   topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                "snippet": topic["Text"],
                "url":     topic.get("FirstURL", ""),
            })

    return results[:max_results]


# ---------------------------------------------------------------------------
# Groq summarisation
# ---------------------------------------------------------------------------

def _summarise(query: str, results: list[dict]) -> str:
    """Ask Groq 8b to summarise search results into one short answer."""
    if not results:
        return "nothing useful came up."

    snippets = "\n".join(
        f"- {r['snippet']}" for r in results if r.get("snippet")
    )

    prompt = (
        f"Search results for: {query}\n\n"
        f"{snippets}\n\n"
        f"Give a concise answer in 1-2 sentences. "
        f"No preamble. No 'based on the results'. Just the answer."
    )

    payload = json.dumps({
        "model":      _SEARCH_MODEL,
        "max_tokens": _MAX_TOKENS,
        "messages": [
            {
                "role":    "system",
                "content": (
                    f"You are {KIKI_NAME}, a terse AI assistant. "
                    "Answer in 1-2 short sentences. No fluff."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        # fallback: just return the first snippet
        return results[0]["snippet"] if results else f"search failed: {e}"


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def _extract_query(message: str) -> str:
    """Strip trigger phrases to get the actual search query."""
    msg = message.lower().strip()
    for trigger in (
        "search for", "search the web for", "search the web",
        "look up", "find me", "find information about",
        "find", "google", "what is", "what are", "who is",
        "search",
    ):
        if msg.startswith(trigger):
            return message[len(trigger):].strip()
    return message


def run(query: str = "", **kwargs) -> str:
    search_query = _extract_query(query)
    if not search_query:
        return "what do you want me to search for?"

    try:
        results = _ddg_search(search_query)
    except RuntimeError as e:
        return str(e)

    if not results:
        return f"nothing useful found for '{search_query}'."

    return _summarise(search_query, results)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    assert _extract_query("search for python tutorials") == "python tutorials"
    assert _extract_query("look up the news today")      == "the news today"
    assert _extract_query("find me a pasta recipe")      == "a pasta recipe"
    assert _extract_query("google machine learning")     == "machine learning"
    assert _extract_query("what is a black hole")        == "a black hole"

    print("testing live search (needs network)...")
    result = run(query="what is a black hole")
    assert result, "empty result"
    assert len(result) > 10, f"result too short: {result!r}"
    print(f"result: {result}")

    print("web_search.py — all tests passed.")