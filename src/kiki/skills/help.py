"""
Skill: help
Kiki explains herself. Auto-generates skill list from the registry at runtime.
"""
from __future__ import annotations

NAME        = "help"
DESCRIPTION = "help explain how to use yourself capabilities instructions guide"
EXAMPLES    = [
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
]
PARAMETERS      = {}
REQUIRES_VISION = False

# ---------------------------------------------------------------------------
# Static help content
# ---------------------------------------------------------------------------

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

_SKILLS_HEADER = "skills:"

_CUSTOM = """
custom skills:
  drop a .py file in the skills/ folder.
  define NAME, DESCRIPTION, EXAMPLES, and run().
  kiki picks it up on next launch. no registration needed.
""".strip()

_ABOUT = """
about:
  i'm kiki. named after the bouba/kiki effect — round thing, sharp name.
  i live on your screen and try to stay out of the way.
  built with PyQt6, Groq, and a 17MB local semantic model.
""".strip()


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(**kwargs) -> str:
    # lazy import to avoid circular deps at module load time
    registry = kwargs.get("registry")

    lines = [
        _CONTROLS,
        "",
        _MOODS,
        "",
    ]

    # auto-generate skill list from registry if available
    if registry is not None:
        skills = registry.all_skills()
        skill_lines = [_SKILLS_HEADER]
        for skill in skills:
            if skill.name == "help":
                continue
            example = skill.examples[0] if skill.examples else ""
            skill_lines.append(f'  {skill.name:<16} — e.g. "{example}"')
        lines += skill_lines
    else:
        lines.append(_SKILLS_HEADER)
        lines.append("  (registry unavailable)")

    lines += ["", _CUSTOM, "", _ABOUT]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # without registry
    result = run()
    assert "controls"  in result
    assert "moods"     in result
    assert "kiki"      in result
    assert "skills:"   in result
    print("help.py (no registry) — passed.")

    # with stub registry
    class _StubSkill:
        name     = "open_app"
        examples = ["open chrome"]

    class _StubRegistry:
        def all_skills(self):
            return [_StubSkill()]

    result = run(registry=_StubRegistry())
    assert "open_app"    in result
    assert "open chrome" in result
    print("help.py (with registry) — passed.")

    print("help.py — all tests passed.")
    print()
    print("--- preview ---")
    print(run(registry=_StubRegistry()))