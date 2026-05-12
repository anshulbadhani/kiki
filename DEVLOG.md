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
- **3:04 PM:** Claude limit reached 🙃
- **3:12 PM:** I was manually fixing the bugs, when I realised that I have to copy paste same if conditions if I would have to add something new. Which defeats the purpose of the FSM in the first place. I would have to be aware of this pattern if I could make an MVP of this. Maybe this could go in 10 more hours wala thing
- **3:32 PM:** I think I should take some rest now, I will write here when I come back after a break. Maybe study for exams, idk
- **5:20 PM:** Getting back to the work
- **5:33 PM:** Always on top is not working with WSLg. So, I will move to windows native (would have to setup python from scratch T_T)
- **6:07 PM:** Update: I made it work and this dude is soo cutee. Lol I spent a lot of time playing with it. Now, I will take a break from dev and study Linear Algebra for exams 🙄
- **8:35 PM:** Started devlopment again
- **9:00 PM:** Done with all the basic UI and chat features. I would like to make it more alive and add some "intelligence" to it by writing basic scripts to do basic stuff like alarms and calendar updates.