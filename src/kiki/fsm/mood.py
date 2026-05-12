from __future__ import annotations
from .base import State, FSM
from ..config import (
    MOOD_TICK_MS,
    MOOD_DECAY_PER_TICK,
    HARASSMENT_INCREMENT,
    ANNOYED_THRESHOLD,
    GRUMPY_THRESHOLD,
    IDLE_TIMEOUT_MS,
)


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class Calm(State):
    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "harassment":
            self.fsm.score += HARASSMENT_INCREMENT
            if self.fsm.score >= ANNOYED_THRESHOLD:
                return "Annoyed"
        elif event == "tick":
            self.fsm.score = max(0.0, self.fsm.score - MOOD_DECAY_PER_TICK)
            if self.fsm.idle_ms >= IDLE_TIMEOUT_MS:
                return "Idle"
        return None


class Annoyed(State):
    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "harassment":
            self.fsm.score += HARASSMENT_INCREMENT
            if self.fsm.score >= GRUMPY_THRESHOLD:
                return "Grumpy"
        elif event == "tick":
            self.fsm.score = max(0.0, self.fsm.score - MOOD_DECAY_PER_TICK)
            if self.fsm.score < ANNOYED_THRESHOLD:
                return "Recovering"
        return None


class Grumpy(State):
    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "tick":
            self.fsm.score = max(0.0, self.fsm.score - MOOD_DECAY_PER_TICK)
            if self.fsm.score < GRUMPY_THRESHOLD:
                return "Recovering"
        return None


class Recovering(State):
    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "harassment":
            self.fsm.score += HARASSMENT_INCREMENT
            if self.fsm.score >= GRUMPY_THRESHOLD:
                return "Grumpy"
            if self.fsm.score >= ANNOYED_THRESHOLD:
                return "Annoyed"
        elif event == "tick":
            self.fsm.score = max(0.0, self.fsm.score - MOOD_DECAY_PER_TICK)
            if self.fsm.score == 0.0:
                return "Calm"
        return None


class Idle(State):
    def on_enter(self) -> None:
        self.fsm.idle_ms = 0

    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "any_input":
            return "Calm"
        return None


# ---------------------------------------------------------------------------
# MoodFSM
# ---------------------------------------------------------------------------

class MoodFSM(FSM):
    """
    Tracks Kiki's emotional state as a numeric score (0–100).
    Drive it by calling:
        .tick(delta_ms)   — from a QTimer every MOOD_TICK_MS
        .harass()         — when cursor harassment is detected
        .any_input()      — when user interacts (wakes from idle)
        .truce()          — resets score (e.g. chat opened)
        .pause() / .resume()
    """

    def __init__(self) -> None:
        self.score: float = 0.0
        self.idle_ms: float = 0.0
        self._paused: bool = False

        super().__init__(
            states=[Calm(), Annoyed(), Grumpy(), Recovering(), Idle()],
            initial="Calm",
        )

    def tick(self, delta_ms: float = MOOD_TICK_MS) -> None:
        if self._paused:
            return
        self.idle_ms += delta_ms
        self.send("tick")

    def harass(self) -> None:
        if self._paused:
            return
        self.idle_ms = 0
        self.send("harassment")

    def any_input(self) -> None:
        self.idle_ms = 0
        self.send("any_input")

    def truce(self) -> None:
        """Opening chat = truce. Reset score, go calm."""
        self.score = 0.0
        self.idle_ms = 0.0
        if not self.is_in("Calm"):
            self._transition("Calm")

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @property
    def mood(self) -> str:
        return self.current_name


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    fsm = MoodFSM()
    assert fsm.mood == "Calm"

    # harassment pushes toward annoyed
    for _ in range(5):
        fsm.harass()
    assert fsm.mood == "Annoyed", f"expected Annoyed, got {fsm.mood}"

    # more harassment → grumpy
    for _ in range(10):
        fsm.harass()
    assert fsm.mood == "Grumpy", f"expected Grumpy, got {fsm.mood}"

    # decay back through recovering → calm
    while fsm.mood != "Calm":
        fsm.tick(MOOD_TICK_MS)
    assert fsm.mood == "Calm"

    # truce resets immediately
    for _ in range(5):
        fsm.harass()
    fsm.truce()
    assert fsm.mood == "Calm"
    assert fsm.score == 0.0

    # idle after timeout
    fsm.idle_ms = IDLE_TIMEOUT_MS
    fsm.tick(MOOD_TICK_MS)
    assert fsm.mood == "Idle", f"expected Idle, got {fsm.mood}"

    # any input wakes from idle
    fsm.any_input()
    assert fsm.mood == "Calm"

    print("fsm/mood.py — all tests passed.")