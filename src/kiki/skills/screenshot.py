from __future__ import annotations
import base64
import io
from dataclasses import dataclass, field

from .base import Skill
from ..config import GROQ_API_KEY, VISION_MODEL


@dataclass
class ScreenshotSkill(Skill):
    name:        str       = "screenshot"
    description: str       = "screenshot describe screen look see what is on screen vision"
    examples:    list[str] = field(default_factory=lambda: [
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
    ])
    category:        str  = "vision"
    parameters:      dict = field(default_factory=lambda: {"query": "full user message"})
    requires_vision: bool = False   # we take the screenshot ourselves

    def run(self, query: str = "", **kwargs) -> str:
        try:
            img = self._take_screenshot()
        except RuntimeError as e:
            return str(e)
        try:
            b64 = self._image_to_base64(img)
        except Exception as e:
            return f"failed to process screenshot: {e}"
        try:
            return self._describe(b64, query)
        except Exception as e:
            return f"vision failed: {e}"

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _take_screenshot(self):
        try:
            from PIL import ImageGrab
            return ImageGrab.grab()
        except Exception as e:
            raise RuntimeError(f"screenshot failed: {e}")

    def _image_to_base64(self, img) -> str:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return base64.b64encode(buf.getvalue()).decode()

    def _describe(self, image_b64: str, query: str) -> str:
        from groq import Groq
        client   = Groq(api_key=GROQ_API_KEY)
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
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    skill = ScreenshotSkill()

    print("taking screenshot...")
    img = skill._take_screenshot()
    assert img is not None
    print(f"screenshot size: {img.size}")

    print("encoding to base64...")
    b64 = skill._image_to_base64(img)
    assert len(b64) > 100
    print(f"base64 length: {len(b64)}")

    print("sending to groq vision...")
    result = skill.run(query="what am I looking at")
    assert result, "empty result"
    print(f"result: {result}")

    print("screenshot.py — all tests passed.")