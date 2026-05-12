# skills/base.py
from abc import ABC, abstractmethod

class Skill(ABC):
    name:            str
    description:     str
    examples:        list[str]
    category:        str = "other"
    parameters:      dict[str, str] = {}
    requires_vision: bool = False

    @abstractmethod
    def run(self, **kwargs) -> str: ...

    @property
    def corpus(self) -> str:
        return " ".join([self.description] + self.examples)