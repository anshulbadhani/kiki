from __future__ import annotations
import threading
from groq import Groq
from .config import (
    GROQ_API_KEY,
    MODEL,
    MAX_TOKENS,
    SYSTEM_PROMPT_CALM,
    SYSTEM_PROMPT_ANNOYED,
    SYSTEM_PROMPT_GRUMPY,
)


# ---------------------------------------------------------------------------
# Mood → system prompt
# ---------------------------------------------------------------------------

MOOD_PROMPTS: dict[str, str] = {
    "Calm":       SYSTEM_PROMPT_CALM,
    "Recovering": SYSTEM_PROMPT_CALM,
    "Idle":       SYSTEM_PROMPT_CALM,
    "Annoyed":    SYSTEM_PROMPT_ANNOYED,
    "Grumpy":     SYSTEM_PROMPT_GRUMPY,
}


# ---------------------------------------------------------------------------
# Brain
# ---------------------------------------------------------------------------

class Brain:
    """
    Wraps the Groq client. Maintains conversation history.
    All LLM calls happen on a background thread so the UI never blocks.

    Usage:
        brain = Brain()
        brain.chat(
            message   = "what should I work on",
            mood      = "Grumpy",
            on_token  = lambda token: ...,   # called for each streamed chunk
            on_done   = lambda full: ...,    # called when stream ends
            on_error  = lambda err:  ...,    # called on exception
        )
    """

    def __init__(self) -> None:
        self._client  = Groq(api_key=GROQ_API_KEY)
        self._history: list[dict] = []   # [{role, content}, ...]
        self._lock    = threading.Lock()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def chat(
        self,
        message:  str,
        mood:     str,
        on_token: callable,
        on_done:  callable,
        on_error: callable,
    ) -> None:
        """Non-blocking. Spawns a daemon thread for the LLM call."""
        thread = threading.Thread(
            target=self._stream,
            args=(message, mood, on_token, on_done, on_error),
            daemon=True,
        )
        thread.start()

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _stream(
        self,
        message:  str,
        mood:     str,
        on_token: callable,
        on_done:  callable,
        on_error: callable,
    ) -> None:
        try:
            with self._lock:
                self._history.append({"role": "user", "content": message})
                history_snapshot = list(self._history)

            system = MOOD_PROMPTS.get(mood, SYSTEM_PROMPT_CALM)

            stream = self._client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    *history_snapshot,
                ],
                stream=True,
            )

            full_response = []
            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    full_response.append(token)
                    on_token(token)

            reply = "".join(full_response)

            with self._lock:
                self._history.append({"role": "assistant", "content": reply})

            on_done(reply)

        except Exception as e:
            on_error(e)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os, time
    from dotenv import load_dotenv
    load_dotenv()

    brain = Brain()
    tokens = []
    done   = []
    errors = []

    brain.chat(
        message  = "say exactly: ok.",
        mood     = "Calm",
        on_token = lambda t: tokens.append(t),
        on_done  = lambda r: done.append(r),
        on_error = lambda e: errors.append(e),
    )

    # wait for the thread
    timeout = time.time() + 10
    while not done and not errors and time.time() < timeout:
        time.sleep(0.1)

    assert not errors, f"Error: {errors[0]}"
    assert len(tokens) > 0, "No tokens received"
    assert len(done) == 1, "on_done not called"
    print(f"Response: {''.join(tokens)!r}")

    # second message uses history
    tokens2 = []
    done2   = []
    brain.chat(
        message  = "what did I just ask you to say?",
        mood     = "Calm",
        on_token = lambda t: tokens2.append(t),
        on_done  = lambda r: done2.append(r),
        on_error = lambda e: errors.append(e),
    )

    timeout = time.time() + 10
    while not done2 and not errors and time.time() < timeout:
        time.sleep(0.1)

    assert not errors, f"Error: {errors[0]}"
    print(f"History response: {''.join(tokens2)!r}")

    print("brain.py — all tests passed.")