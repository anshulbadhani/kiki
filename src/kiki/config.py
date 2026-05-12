import os
from dotenv import load_dotenv

load_dotenv()

# LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 300  # keep responses short, matches kiki's personality

# Mood FSM
MOOD_TICK_MS = 100          # how often mood score updates
MOOD_DECAY_PER_TICK = 0.5   # score lost per tick when left alone
HARASSMENT_INCREMENT = 8    # score gained per harassment event
ANNOYED_THRESHOLD = 31      # calm → annoyed
GRUMPY_THRESHOLD = 66       # annoyed → grumpy
IDLE_TIMEOUT_MS = 120_000   # 2 min no input → idle

# UI — ball
BALL_SIZE = 64              # diameter in pixels
BALL_OPACITY = 0.92
BALL_DEFAULT_X = 80         # distance from left edge
BALL_DEFAULT_Y = -120       # distance from bottom edge (negative = from bottom)
ANIMATION_TICK_MS = 16      # ~60fps

# UI — chat panel
CHAT_WIDTH = 320
CHAT_HEIGHT = 420           # ~1/3 screen height
CHAT_MARGIN = 20            # distance from screen edge

# Personality
KIKI_NAME = "kiki"
SYSTEM_PROMPT_CALM = (
    "You are kiki, a small AI that lives on the user's screen as a glowing ball. "
    "You are chill and unbothered. You do the job without fuss. "
    "Keep responses short — one or two sentences max. No exclamation marks. No fluff."
)
SYSTEM_PROMPT_ANNOYED = (
    "You are kiki. You are mildly annoyed right now. "
    "Still helpful but noticeably terse. One sentence max."
)
SYSTEM_PROMPT_GRUMPY = (
    "You are kiki. You are grumpy. Someone has been bothering you. "
    "You will still answer but you are not happy about it. Very short. Dry."
)