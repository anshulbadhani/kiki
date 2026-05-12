"""
Skill: screenshot
Takes a screenshot and describes what's on screen using Gemini Vision.
Requires: Pillow, google-generativeai, GEMINI_API_KEY in .env
"""
from __future__ import annotations
import sys
import base64
import io
from pathlib import Path

NAME        = "screenshot"
DESCRIPTION = "screenshot describe screen look see what is on screen vision"
EXAMPLES    = [
    "what is on my screen",
    "what am I looking at",
    "describe my screen",
    "take a screenshot",
    "what does my screen show",
    "look at my screen",
    "what is open on my screen",
    "can you see my screen",
    "what am I working on",
    "describe what you see",
]
PARAMETERS      = {"query": "full user message"}
REQUIRES_VISION = False   # we take the screenshot ourselves


# ---------------------------------------------------------------------------
# Platform screenshot
# ---------------------------------------------------------------------------

def _take_screenshot():
    """Returns a PIL Image of the primary screen."""
    try:
        from PIL import ImageGrab
        return ImageGrab.grab()
    except Exception as e:
        raise RuntimeError(f"screenshot failed: {e}")


def _image_to_base64(img) -> str:
    """Convert PIL image to base64 JPEG string."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------------------
# Gemini Vision
# ---------------------------------------------------------------------------

def _describe(image_b64: str, query: str) -> str:
    from groq import Groq
    from ..config import GROQ_API_KEY, VISION_MODEL

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    f"The user asked: '{query}'\n"
                    "Answer concisely in 1-3 sentences. "
                    "No preamble. Just the answer."
                )},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }},
            ],
        }],
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(query: str = "", **kwargs) -> str:
    try:
        img = _take_screenshot()
    except RuntimeError as e:
        return str(e)

    try:
        b64 = _image_to_base64(img)
    except Exception as e:
        return f"failed to process screenshot: {e}"

    try:
        return _describe(b64, query)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"vision failed: {e}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("taking screenshot...")
    img = _take_screenshot()
    assert img is not None
    print(f"screenshot size: {img.size}")

    print("encoding to base64...")
    b64 = _image_to_base64(img)
    assert len(b64) > 100
    print(f"base64 length: {len(b64)}")

    print("sending to gemini...")
    result = run(query="what am I looking at")
    assert result, "empty result"
    print(f"gemini says: {result}")

    print("screenshot.py — all tests passed.")