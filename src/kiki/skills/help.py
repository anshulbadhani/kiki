from __future__ import annotations
from dataclasses import dataclass, field
from .base import Skill


_CONTROLS = """
controls:
  click       — open / close chat
  drag        — move me anywhere on screen
  hover spam  — I get grumpy. stop it.
  right click — settings / quit
""".strip()

_MOODS = """
moods:
  calm        — default. just vibing.
  annoyed     — you've been poking me.
  grumpy      — you really went for it.
  recovering  — cooling down, give me a minute.
  idle        — left alone too long. poke me to wake up.
""".strip()

_CUSTOM = """
custom skills:
  drop a .py file in the skills/ folder.
  subclass Skill, implement run().
  kiki picks it up on next launch. no registration needed.
""".strip()

_ABOUT = """
about:
  i'm kiki. named after the bouba/kiki effect — round thing, sharp name.
  i live on your screen and try to stay out of the way.
  built with PyQt6, Groq, and a 17MB local semantic model.
""".strip()


@dataclass
class HelpSkill(Skill):
    name:        str       = "help"
    description: str       = "help explain how to use yourself capabilities instructions guide"
    examples:    list[str] = field(default_factory=lambda: [
        "help",
        "how do I use you",
        "what can you do",
        "how does this work",
        "what are you",
        "show me what you can do",
        "how do I talk to you",
        "what skills do you have",
        "explain yourself",
        "who are you",
    ])
    category:   str  = "meta"
    parameters: dict = field(default_factory=dict)

    def run(self, **kwargs) -> str:
        registry = kwargs.get("registry")
        lines = [_CONTROLS, "", _MOODS, ""]

        if registry is not None:
            skill_lines = ["skills:"]
            for skill in registry.all_skills():
                if skill.name == "help":
                    continue
                example = skill.examples[0] if skill.examples else ""
                skill_lines.append(f'  {skill.name:<16} — e.g. "{example}"')
            lines += skill_lines
        else:
            lines += ["skills:", "  (registry unavailable)"]

        lines += ["", _CUSTOM, "", _ABOUT]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    skill = HelpSkill()

    result = skill.run()
    assert "controls" in result
    assert "moods"    in result
    assert "kiki"     in result
    assert "skills:"  in result
    print("help.py (no registry) — passed.")

    class _StubSkill:
        name     = "open_app"
        examples = ["open chrome"]

    class _StubRegistry:
        def all_skills(self):
            return [_StubSkill()]

    result = skill.run(registry=_StubRegistry())
    assert "open_app"    in result
    assert "open chrome" in result
    print("help.py (with registry) — passed.")
    print("help.py — all tests passed.")
    print()
    print("--- preview ---")
    print(skill.run(registry=_StubRegistry()))