"""
Skill: clipboard
Read from or write to the system clipboard. Cross-platform via pyperclip.
"""
from __future__ import annotations
import pyperclip

NAME        = "clipboard"
DESCRIPTION = "copy paste clipboard read write text"
EXAMPLES    = [
    "copy this to clipboard",
    "what is in my clipboard",
    "paste clipboard content",
    "read my clipboard",
    "copy text to clipboard",
    "what did I copy",
    "show clipboard",
    "get clipboard content",
]
PARAMETERS      = {"query": "full user message"}
REQUIRES_VISION = False

READ_TRIGGERS  = {"read", "show", "what", "get", "paste", "whats", "what's"}
WRITE_TRIGGERS = {"copy", "write", "set", "save"}


def _intent(message: str) -> str:
    """Returns 'read' or 'write'."""
    first_word = message.lower().strip().split()[0]
    if first_word in WRITE_TRIGGERS:
        return "write"
    for word in READ_TRIGGERS:
        if word in message.lower():
            return "read"
    return "read"


def _extract_text(message: str) -> str:
    """Extract text to copy — everything after trigger word."""
    msg = message.strip()
    for trigger in ("copy", "write", "set", "save"):
        lower = msg.lower()
        idx   = lower.find(trigger)
        if idx != -1:
            after = msg[idx + len(trigger):].strip()
            # strip filler words
            for filler in ("this", "to clipboard", "the following", ":"):
                after = after.replace(filler, "").strip()
            if after:
                return after
    return ""


def run(query: str = "", **kwargs) -> str:
    intent = _intent(query)

    if intent == "read":
        try:
            content = pyperclip.paste()
            if not content:
                return "clipboard is empty."
            preview = content[:120]
            suffix  = "..." if len(content) > 120 else ""
            return f"clipboard: {preview}{suffix}"
        except Exception as e:
            return f"couldn't read clipboard: {e}"

    if intent == "write":
        text = _extract_text(query)
        if not text:
            return "what do you want me to copy?"
        try:
            pyperclip.copy(text)
            return f"copied to clipboard."
        except Exception as e:
            return f"couldn't write to clipboard: {e}"

    return "not sure what you want me to do with the clipboard."


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    assert _intent("read my clipboard")        == "read"
    assert _intent("what is in my clipboard")  == "read"
    assert _intent("show clipboard")           == "read"
    assert _intent("copy hello world")         == "write"
    assert _intent("copy this to clipboard")   == "write"

    assert _extract_text("copy hello world")            == "hello world"
    assert _extract_text("copy this to clipboard")      == ""
    assert _extract_text("copy the following: foo bar") == "foo bar"

    # live clipboard test
    pyperclip.copy("kiki test string")
    result = run(query="read my clipboard")
    assert "kiki test string" in result, f"unexpected: {result}"

    result = run(query="copy hello from kiki")
    assert result == "copied to clipboard."
    assert pyperclip.paste() == "hello from kiki"

    result = run(query="what is in my clipboard")
    assert "hello from kiki" in result

    print("clipboard.py — all tests passed.")