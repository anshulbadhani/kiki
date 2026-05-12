from __future__ import annotations
import threading
from groq import Groq

from .config import (
    GROQ_API_KEY, MODEL, MAX_TOKENS,
    SYSTEM_PROMPT_CALM, SYSTEM_PROMPT_ANNOYED, SYSTEM_PROMPT_GRUMPY,
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
    Single entry point for all of kiki's intelligence.

    Routing logic:
        1. Try skill registry (local ONNX, free, instant)
        2. Fall back to Groq LLM (streamed, mood-aware, costs API credits)

    Skill results are added to history so LLM has context for follow-ups.

    Usage:
        brain = Brain()
        brain.chat(
            message  = "open chrome",
            mood     = "Calm",
            on_token = lambda token: ...,
            on_done  = lambda full:  ...,
            on_error = lambda err:   ...,
        )
    """

    def __init__(self) -> None:
        self._client  = Groq(api_key=GROQ_API_KEY)
        self._history: list[dict] = []
        self._lock    = threading.Lock()
        self._registry = self._load_registry()

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
        """Non-blocking. Routes to skill or LLM on a daemon thread."""
        thread = threading.Thread(
            target  = self._route,
            args    = (message, mood, on_token, on_done, on_error),
            daemon  = True,
        )
        thread.start()

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # -----------------------------------------------------------------------
    # Routing
    # -----------------------------------------------------------------------

    def _route(
        self,
        message:  str,
        mood:     str,
        on_token: callable,
        on_done:  callable,
        on_error: callable,
    ) -> None:
        try:
            # record user message
            with self._lock:
                self._history.append({"role": "user", "content": message})

            # try skill first
            if self._registry is not None:
                result = self._registry.route(message)
                if result is not None:
                    on_token(result)
                    with self._lock:
                        self._history.append({
                            "role":    "assistant",
                            "content": result,
                        })
                    on_done(result)
                    return

            # no skill match — fall back to LLM
            self._stream(message, mood, on_token, on_done, on_error)

        except Exception as e:
            on_error(e)

    # -----------------------------------------------------------------------
    # LLM stream
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
                history_snapshot = list(self._history)

            system = MOOD_PROMPTS.get(mood, SYSTEM_PROMPT_CALM)

            stream = self._client.chat.completions.create(
                model      = MODEL,
                max_tokens = MAX_TOKENS,
                messages   = [
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

    # -----------------------------------------------------------------------
    # Registry loader — graceful degradation if ONNX model not ready
    # -----------------------------------------------------------------------

    def _load_registry(self):
        try:
            from .skills.encoder   import Encoder
            from .skills.registry  import Registry
            encoder  = Encoder()
            registry = Registry(encoder)
            print(f"[brain] skill registry loaded: {len(registry)} skills")
            return registry
        except FileNotFoundError:
            print(
                "[brain] ONNX model not found — skill routing disabled.\n"
                "        run: uv run python -m kiki.setup"
            )
            return None
        except Exception as e:
            print(f"[brain] registry failed to load ({e}) — LLM-only mode")
            return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time
    from dotenv import load_dotenv
    load_dotenv()
    import time

    brain  = Brain()
    tokens = []
    done   = []
    errors = []

    def reset():
        tokens.clear()
        done.clear()
        errors.clear()

    def wait(timeout: float = 10.0) -> bool:
        deadline = time.time() + timeout
        while not done and not errors and time.time() < deadline:
            time.sleep(0.05)
        return bool(done)

    # --- skill routing test (needs registry) ---
    if brain._registry is not None:
        reset()
        brain.chat(
            message  = "read my clipboard",
            mood     = "Calm",
            on_token = lambda t: tokens.append(t),
            on_done  = lambda r: done.append(r),
            on_error = lambda e: errors.append(e),
        )
        assert wait(), "timed out"
        assert not errors, f"error: {errors[0]}"
        result = "".join(tokens)
        print(f"skill result: {result!r}")
        # skill result should not have been streamed token-by-token
        assert len(tokens) == 1, f"expected 1 token for skill, got {len(tokens)}"
        print("skill routing — passed.")
    else:
        print("skill routing — skipped (no registry)")

    # --- LLM fallback test ---
    reset()
    brain.chat(
        message  = "say exactly: ok.",
        mood     = "Calm",
        on_token = lambda t: tokens.append(t),
        on_done  = lambda r: done.append(r),
        on_error = lambda e: errors.append(e),
    )
    assert wait(), "timed out"
    assert not errors,      f"error: {errors[0]}"
    assert len(tokens) > 0, "no tokens received"
    print(f"LLM result: {''.join(tokens)!r}")
    print("LLM fallback — passed.")

    # --- history carries across turns ---
    reset()
    brain.chat(
        message  = "what did I just ask you to say?",
        mood     = "Calm",
        on_token = lambda t: tokens.append(t),
        on_done  = lambda r: done.append(r),
        on_error = lambda e: errors.append(e),
    )
    assert wait(), "timed out"
    assert not errors, f"error: {errors[0]}"
    print(f"history result: {''.join(tokens)!r}")
    print("history — passed.")

    print("\nbrain.py — all tests passed.")

# if __name__ == "__main__":
#     from dotenv import load_dotenv
#     load_dotenv()
#     import time

#     brain  = Brain()
#     tokens = []
#     done   = []
#     errors = []

#     def reset():
#         tokens.clear()
#         done.clear()
#         errors.clear()

#     def wait(timeout: float = 10.0) -> bool:
#         deadline = time.time() + timeout
#         while not done and not errors and time.time() < deadline:
#             time.sleep(0.05)
#         print(f"[wait] done={done} errors={errors} tokens={tokens}")
#         return bool(done)

#     reset()
#     brain.chat(
#         message  = "read my clipboard",
#         mood     = "Calm",
#         on_token = lambda t: (print(f"[token] {t!r}"), tokens.append(t)),
#         on_done  = lambda r: (print(f"[done] {r!r}"), done.append(r)),
#         on_error = lambda e: (print(f"[error] {e!r}"), errors.append(e)),
#     )
#     wait()