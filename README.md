<!-- # Kiki
A small, moody AI that lives on your screen. It is highly recommended to have a look at [devlog.md](./DEVLOG.md)

### TODOs
- [x] Write readme
    - [x] how to setup
    - [x] how to contribute
    - [x] features
    - [x] future plans 
    - [x] include claude generated design ideas
    - [x] excalidraw diagrams for state machines or entire system arch if needed
- [ ] Record a demo video and include in README
-->
<!-- (a hackathon at my college where people write different skills would be an awesome idea) -->


# 🔮 Kiki
**A small, moody AI that lives on your screen.**

> 📖 **Note:** Kiki was built in a 10-hour intensive sprint as a technical showcase for the **Activate AI Fellows (Summer 2026)** application. Read the [DEVLOG.md](./DEVLOG.md) to see how we battled PyInstaller, WSL containers, and Python's dynamic import machinery to bring her to life.

Kiki is not just a chatbot; she's a stateful, locally-aware desktop companion. She handles your daily tasks, opens applications, searches the web, and holds a genuine grudge if you annoy her. 


## ✨ Features

*   **Persistent Personality (Dual-FSM):** Kiki has boundaries. If you rapidly click her, drag her around, or insult her, her Mood Finite State Machine tracks the harassment. She will get "Annoyed" or "Grumpy," her orb avatar will turn red, and she will actively inject her bad mood into her LLM responses until she calms down (or you apologize).
*   **Drop-In Dynamic Plugins:** Kiki features a completely extensible Python plugin architecture. Drop a raw `.py` file into her local AppData folder, and she will dynamically compile and absorb the skill on her next boot—no recompiling required.
*   **Hybrid Neural Routing:** Kiki uses a local ONNX embedding model (`paraphrase-MiniLM-L3-v2`) to instantly route user commands to local Python skills. If she doesn't have a skill for it, she seamlessly falls back to the Groq LLM API for conversational responses.
*   **Secure & Local-First:** Your Groq API key is asked for natively on the first boot and stored safely in your OS-level `secrets.json`. 


## 🏗️ System Architecture & State Machines

Kiki's brain is split into a physical interaction tracker (Mode) and an emotional tracker (Mood).

### The Mood FSM
```mermaid
stateDiagram-v2
    [*] --> Calm
    Calm --> Annoyed : Harassment / Insults
    Annoyed --> Grumpy : Continued Harassment
    Grumpy --> Recovering : Idle Time (Decay)
    Recovering --> Calm : Idle Time (Decay)
    Annoyed --> Calm : User Apologizes
    Calm --> Idle : Extended Timeout
    Idle --> Calm : Any Interaction

```

### The Hybrid Routing Brain

```mermaid
flowchart TD
    User[User Input] --> Embed[Local ONNX Encoder]
    Embed --> Registry{Skill Registry Match?}
    Registry -- Match > 0.6 --> Skill[Execute Local Python Skill]
    Registry -- No Match --> Groq[Groq LLM Stream]
    Skill --> Output[Chat Bubble]
    Groq --> Output
    Output --> FSM[Update Mood/Memory]

```

## 🚀 How to Setup

### Option 1: For Users (The easy way)

1. Go to the [Releases](https://github.com/anshulbadhani/kiki/releases/tag/v1.0.0) tab and download the latest `.zip` for your OS (Windows `.exe` or Linux binary).
2. Extract the folder and run the `kiki` executable.
3. On the first boot, Kiki will prompt you for a **Groq API Key** (get one for free at [console.groq.com](https://console.groq.com/).
4. Click her orb to open the chat!

### Option 2: For Developers (From Source)

Kiki uses `uv` for lightning-fast dependency management.

```bash
# 1. Clone the repo
git clone https://github.com/anshulbadhani/kiki.git
cd kiki

# 2. Sync dependencies
uv sync

# 3. Download the local ONNX routing models
uv run -m kiki.setup

# 4. Run Kiki
uv run -m kiki.main

```

---

## 🛠️ How to Contribute (Adding Custom Skills)

Kiki was designed to be customized. To create a skill, simply write a `.py` file and drop it in Kiki's skill folder (`~/.local/share/kiki/skills/` on Linux/WSL, or `%APPDATA%\kiki\skills\` on Windows).

**Example Skill (`toggle_darkmode.py`):**

```python
from kiki.skills.base import Skill

class DarkModeSkill(Skill):
    name = "dark_mode"
    corpus = [ # more examples = better searching for kiki
        "turn on dark mode",
        "switch to light theme",
        "change system theme",
    ]

    def execute(self, query: str) -> str:
        # Your python logic here!
        return "I've toggled your system theme. Happy hacking!"

```

On her next boot, Kiki will automatically generate vector embeddings for your `corpus` phrases and route relevant questions directly to your script.

For actual implementation you can refer to [open_app example skill](./example/skills/open_app.py) or [skills/](./src/kiki/skills/)

---

## 🔮 Future Plans

* [ ] **Bundle ONNX by Default:** Integrate the ~100MB ONNX model directly into the PyInstaller build so developers don't have to run `setup.py`.
* [ ] **Community Skill Hub:** Create a centralized CLI command to download verified skills created by other users (e.g., `kiki install spotify-controller`).
* [ ] **Cross-Platform UI Parity:** Overcome WSL/Linux container limitations (like `dbus` notifications and X11 screenshots) to make Kiki fully feature-complete on Linux.
* [ ] **Voice Integration:** Allow Kiki to hear and speak using lightweight local TTS/STT models.
* [ ] **Ability to Click and Move:** So, kiki can help you finding toggles and buttons on complex UIs or help you learn something new.
* [ ] **Cutsom LLM Options:** Make LLM component more modular so you can choose to use a local model or some other API.
* [ ] **SDK:** For better DX (Developer Experience) while making new skills for kiki.

---

## 🎨 Design & Inspiration

* **The Orb Aesthetic:** The translucent, glowing, frameless window design was heavily inspired by classic desktop pets and modern floating AI interfaces.
* **Color Theory:** Kiki's default calm blue `#508CDC` gradients shift smoothly into harsh reds `#B43232` when her FSM detects agitation, providing immediate, non-verbal feedback to the user.
