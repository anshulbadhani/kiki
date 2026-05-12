# Devlog — Kiki
Starting this for the Activate AI Fellows challenge. 6-10 hour budget.

The idea: a small AI that lives on your screen as a ball. No face. Just presence.
Named it Kiki – after the bouba/kiki effect. It's a round thing called Kiki (hehe).

Spent time designing before writing any code. Two state machines:
- MoodFSM: calm → annoyed → grumpy → recovering → idle
- ModeFSM: orb → chat open → thinking → responding → dragging

Mood is score-based (0–100), not event-driven. A timer decays it slowly.
The two FSMs are independent but send signals to each other at 4 defined points.

Stack: Python 3.12, PyQt6, Groq API (llama-3.3-70b), uv for packaging.

## 12th May 2026
- **2:31 PM:** Starting with fsm/base.py – zero UI dependencies, fully testable headless.