from __future__ import annotations
import urllib.request
import urllib.parse
import json
from dataclasses import dataclass, field

from .base import Skill
from ..config import GROQ_API_KEY, KIKI_NAME


_SEARCH_MODEL = "llama-3.1-8b-instant"
_MAX_TOKENS   = 200


@dataclass
class WebSearchSkill(Skill):
    name:        str       = "web_search"
    description: str       = "search find look up browse information on the web internet google"
    examples:    list[str] = field(default_factory=lambda: [
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
    ])
    category:   str  = "web"
    parameters: dict = field(default_factory=lambda: {
        "query": "full user message"
    })

    def run(self, query: str = "", **kwargs) -> str:
        search_query = self._extract_query(query)
        if not search_query:
            return "what do you want me to search for?"
        try:
            results = self._ddg_search(search_query)
        except RuntimeError as e:
            return str(e)
        if not results:
            return f"nothing useful found for '{search_query}'."
        return self._summarise(search_query, results)

    # -----------------------------------------------------------------------
    # Query extraction
    # -----------------------------------------------------------------------

    def _extract_query(self, message: str) -> str:
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

    # -----------------------------------------------------------------------
    # DuckDuckGo
    # -----------------------------------------------------------------------

    def _ddg_search(self, query: str, max_results: int = 5) -> list[dict]:
        encoded = urllib.parse.quote(query)
        url     = (
            f"https://api.duckduckgo.com/?q={encoded}"
            f"&format=json&no_redirect=1&no_html=1"
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "kiki-ai/0.1"}
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            raise RuntimeError(f"search request failed: {e}")

        results = []
        if data.get("AbstractText"):
            results.append({
                "title":   data.get("Heading", ""),
                "snippet": data["AbstractText"],
                "url":     data.get("AbstractURL", ""),
            })
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title":   topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                    "snippet": topic["Text"],
                    "url":     topic.get("FirstURL", ""),
                })
        return results[:max_results]

    # -----------------------------------------------------------------------
    # Groq summarisation
    # -----------------------------------------------------------------------

    def _summarise(self, query: str, results: list[dict]) -> str:
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
            return results[0]["snippet"] if results else f"search failed: {e}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    skill = WebSearchSkill()

    assert skill._extract_query("search for python tutorials") == "python tutorials"
    assert skill._extract_query("look up the news today")      == "the news today"
    assert skill._extract_query("find me a pasta recipe")      == "a pasta recipe"
    assert skill._extract_query("google machine learning")     == "machine learning"
    assert skill._extract_query("what is a black hole")        == "a black hole"

    print("testing live search (needs network)...")
    result = skill.run(query="what is a black hole")
    assert result and len(result) > 10, f"result too short: {result!r}"
    print(f"result: {result}")

    print("web_search.py — all tests passed.")