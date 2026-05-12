from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import FSM


class State(ABC):
    """Base class for all states in any FSM."""

    def __init__(self) -> None:
        self.fsm: FSM | None = None

    def on_enter(self) -> None:
        """Called when this state becomes active."""
        pass

    def on_exit(self) -> None:
        """Called just before leaving this state."""
        pass

    @abstractmethod
    def handle_event(self, event: str, **kwargs) -> str | None:
        """
        Handle an event. Return the name of the next state to
        transition to, or None to stay in the current state.
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class FSM:
    """
    Generic finite state machine.
    Holds a registry of states and manages transitions.
    """

    def __init__(self, states: list[State], initial: str) -> None:
        self._states: dict[str, State] = {}
        self._callbacks: list[callable] = []

        for state in states:
            state.fsm = self
            self._states[state.name] = state

        if initial not in self._states:
            raise ValueError(f"Initial state '{initial}' not registered.")

        self._current: State = self._states[initial]
        self._current.on_enter()

    @property
    def current(self) -> State:
        return self._current

    @property
    def current_name(self) -> str:
        return self._current.name

    def send(self, event: str, **kwargs) -> bool:
        """
        Send an event to the current state.
        Returns True if a transition occurred.
        """
        next_name = self._current.handle_event(event, **kwargs)

        if next_name is None:
            return False

        if next_name not in self._states:
            raise ValueError(
                f"State '{self._current.name}' returned unknown "
                f"transition target '{next_name}'."
            )

        self._transition(next_name)
        return True

    def _transition(self, next_name: str) -> None:
        prev = self._current
        self._current.on_exit()
        self._current = self._states[next_name]
        self._current.on_enter()

        for cb in self._callbacks:
            cb(prev.name, next_name)

    def on_transition(self, callback: callable) -> None:
        """Register a callback fired on every state change: cb(from_name, to_name)."""
        self._callbacks.append(callback)

    def is_in(self, state_name: str) -> bool:
        return self._current.name == state_name

    def __repr__(self) -> str:
        return f"FSM(current={self._current.name})"

if __name__ == "__main__":
    # --- minimal smoke test ---

    class Idle(State):
        def handle_event(self, event: str, **kwargs) -> str | None:
            if event == "start":
                return "Running"
            return None

    class Running(State):
        def handle_event(self, event: str, **kwargs) -> str | None:
            if event == "stop":
                return "Idle"
            return None

    transitions = []
    fsm = FSM(states=[Idle(), Running()], initial="Idle")
    fsm.on_transition(lambda f, t: transitions.append((f, t)))

    assert fsm.current_name == "Idle"

    result = fsm.send("start")
    assert result is True
    assert fsm.current_name == "Running"

    result = fsm.send("start")  # unknown event in Running
    assert result is False
    assert fsm.current_name == "Running"

    fsm.send("stop")
    assert fsm.current_name == "Idle"
    assert transitions == [("Idle", "Running"), ("Running", "Idle")]

    print("fsm/base.py — all tests passed.")