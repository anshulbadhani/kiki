from __future__ import annotations
import pyperclip
from dataclasses import dataclass, field
from .base import Skill


READ_TRIGGERS  = {"read", "show", "what", "get", "paste", "whats", "what's"}
WRITE_TRIGGERS = {"copy", "write", "set", "save"}


@dataclass
class ClipboardSkill(Skill):
    name:        str       = "clipboard"
    description: str       = "copy paste clipboard read write text"
    examples:    list[str] = field(default_factory=lambda: [
        "copy this to clipboard",
        "what is in my clipboard",
        "paste clipboard content",
        "read my clipboard",
        "copy text to clipboard",
        "what did I copy",
        "show clipboard",
        "get clipboard content",
    ])
    category:   str  = "system"
    parameters: dict = field(default_factory=lambda: {
        "query": "full user message"
    })

    def run(self, query: str = "", **kwargs) -> str:
        intent = self._intent(query)

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
            text = self._extract_text(query)
            if not text:
                return "what do you want me to copy?"
            try:
                pyperclip.copy(text)
                return "copied to clipboard."
            except Exception as e:
                return f"couldn't write to clipboard: {e}"

        return "not sure what you want me to do with the clipboard."

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _intent(self, message: str) -> str:
        first_word = message.lower().strip().split()[0]
        if first_word in WRITE_TRIGGERS:
            return "write"
        for word in READ_TRIGGERS:
            if word in message.lower():
                return "read"
        return "read"

    def _extract_text(self, message: str) -> str:
        msg = message.strip()
        for trigger in ("copy", "write", "set", "save"):
            idx = msg.lower().find(trigger)
            if idx != -1:
                after = msg[idx + len(trigger):].strip()
                for filler in ("this", "to clipboard", "the following", ":"):
                    after = after.replace(filler, "").strip()
                if after:
                    return after
        return ""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    skill = ClipboardSkill()

    assert skill._intent("read my clipboard")       == "read"
    assert skill._intent("what is in my clipboard") == "read"
    assert skill._intent("show clipboard")          == "read"
    assert skill._intent("copy hello world")        == "write"
    assert skill._intent("copy this to clipboard")  == "write"

    assert skill._extract_text("copy hello world")            == "hello world"
    assert skill._extract_text("copy this to clipboard")      == ""
    assert skill._extract_text("copy the following: foo bar") == "foo bar"

    pyperclip.copy("kiki test string")
    result = skill.run(query="read my clipboard")
    assert "kiki test string" in result, f"unexpected: {result}"

    result = skill.run(query="copy hello from kiki")
    assert result == "copied to clipboard."
    assert pyperclip.paste() == "hello from kiki"

    result = skill.run(query="what is in my clipboard")
    assert "hello from kiki" in result

    print("clipboard.py — all tests passed.")
    