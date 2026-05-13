from __future__ import annotations
from .base import State, FSM


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class Orb(State):
    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "click":
            return "ChatOpen"
        elif event == "mouse_down":
            return "Dragging"
        return None


class ChatOpen(State):
    def on_enter(self) -> None:
        # self.fsm.mood_fsm.truce() # resets kiki's mood (for avoiding kiki's tantrums while developing)
        pass

    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "click":
            return "Orb"
        elif event == "send_msg":
            return "Thinking"
        return None


class Dragging(State):
    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "mouse_up":
            return "Orb"
        elif event == "click":        # released as a click, not a drag
            return "ChatOpen"
        return None


class Thinking(State):
    def on_enter(self) -> None:
        self.fsm.mood_fsm.pause()     # pause harassment tracking while busy

    def on_exit(self) -> None:
        self.fsm.mood_fsm.resume()

    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "llm_reply":
            return "Responding"
        return None


class Responding(State):
    def handle_event(self, event: str, **kwargs) -> str | None:
        if event == "done":
            return "ChatOpen"
        return None


# ---------------------------------------------------------------------------
# ModeFSM
# ---------------------------------------------------------------------------

class ModeFSM(FSM):
    """
    Tracks Kiki's interaction mode.
    Drive it by calling:
        .click()        — single click on orb or chat close button
        .mouse_down()   — mouse button pressed on orb
        .mouse_up()     — mouse button released after drag
        .send_msg()     — user submitted a message
        .llm_reply()    — LLM response received, start streaming
        .done()         — streaming complete
    """

    def __init__(self, mood_fsm) -> None:
        self.mood_fsm = mood_fsm

        super().__init__(
            states=[Orb(), ChatOpen(), Dragging(), Thinking(), Responding()],
            initial="Orb",
        )

    def click(self) -> None:
        self.send("click")

    def mouse_down(self) -> None:
        self.send("mouse_down")

    def mouse_up(self) -> None:
        self.send("mouse_up")

    def send_msg(self) -> None:
        self.send("send_msg")

    def llm_reply(self) -> None:
        self.send("llm_reply")

    def done(self) -> None:
        self.send("done")

    @property
    def mode(self) -> str:
        return self.current_name


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from .mood import MoodFSM
    from ..config import MOOD_TICK_MS, HARASSMENT_INCREMENT, ANNOYED_THRESHOLD

    mood = MoodFSM()
    mode = ModeFSM(mood_fsm=mood)

    assert mode.mode == "Orb"

    # click opens chat, triggers truce
    for _ in range(5):
        mood.harass()
    assert mood.mood == "Annoyed"
    mode.click()
    assert mode.mode == "ChatOpen"
    assert mood.mood == "Annoyed"     # truce fired on_enter

    # Only to use while development (Comment assert mood.mood == "Calm" above)
    # assert mood.mood == "Calm"       # truce fired on_enter
    # assert mood.score == 0.0      

    # send message → thinking → responding → back to chat
    mode.send_msg()
    assert mode.mode == "Thinking"
    assert mood._paused             # harassment tracking paused

    mode.llm_reply()
    assert mode.mode == "Responding"
    assert not mood._paused         # resumed on exit of Thinking

    mode.done()
    assert mode.mode == "ChatOpen"

    # close chat → orb
    mode.click()
    assert mode.mode == "Orb"

    # drag flow
    mode.mouse_down()
    assert mode.mode == "Dragging"
    mode.mouse_up()
    assert mode.mode == "Orb"

    # drag that ends as a click → opens chat
    mode.mouse_down()
    assert mode.mode == "Dragging"
    mode.click()
    assert mode.mode == "ChatOpen"

    print("fsm/mode.py — all tests passed.")