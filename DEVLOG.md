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
- **9:00 PM:** Done with all the basic UI and chat features. I would like to make it more alive and add some "intelligence" to it by writing basic scripts to do basic stuff like alarms and calendar updates. But claude limit reached so, I'll do it tomorrow (maybe, or figure out something else).

## 13th May 2026
- **1:21 AM:** Idk I just felt like I should make one more commit before sleeping. So, here I am
- **3:37 AM:** Woah I was not expecting to stay up this late, but damn! I loved working on it. Added a few basic skills. Now, kiki searches in her skillset if she finds a skill then she uses that, else she makes an LLM call. It works good for a prototype. I can submit this as is. But I loved working on it. I can add MCP, add context and attention in chat. Currently, kiki forgets everything and is not able to retain even the last message. Sometimes kiki just gets confused, like if I ask what is at my screen? she replies easily but if I ask her to tell me, "what am I looking at?" She says you're looking at a glowing ball which is me. Which ngl is hella cute. But, that is not what I asked for. Okay, I can forgive her for cuteness. I want to give kiki the ability to move and click on stuff, maybe annoy me? and I really want it to give an ability to say no and figure out fallback scenarios if there is no internet connection. How will she handle it? (maybe sarcastic response or try to brush off in an obvious way, like oh I'm tired kinda thing). And the mood feature is working but I have disabled it for testing purposes so whenever I open my chat she gets happy again, when she should not and I want her to retain her previous mood from last session. Also, in between I realised that the scripts I wrote in previous commit `8b3de32` would make it harder for other people to make their own skills. So, I wrapped it all up on an ABC with @dataclass.

**About 5 hours of total work. Spread across 13 hours**


- **8:00 PM:** Making a release and updating the README
- **8:09 PM:** Okay, I figured out that chat features won't work out of the box. I have to bundle ONNX with exe. So, the end user wont have to install the separately and it works out of the box. I would have to think how will I be approaching the API requests
- **9:17 PM:** I encountered many issues before making an `.exe` to release on github. One of the major issues is user wont have API keys or ONNX model for vector search. But, I have tackled most of it but prompting user before the application starts for an GROQ API key which is stored in the `KIKI_HOME` directory (see [README](./README.md)).
- **9:20 PM:** I have also realised that some features dont work on WSL (due to it being a container and not having most of the UI elements) like screenshots and notifications. I have raised an issue on github. So, for that I will be adding ***community-made skills***.
- **9:58 PM:** My last commit yesterday night was `glued it up...` and I thought I was done. This is my first time shipping a proper python application and now I realise that "lets paste all the `#includes`" approach of C and C++ is way easier to deal with for shipping than Python's dynamic imports 😭. I had to explicitly import everything for the PyInstaller build to actually work (especially the in-built skills).