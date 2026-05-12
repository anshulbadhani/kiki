"""
Abstract base dataclass for all Kiki skills.

Every skill must:
  1. Subclass Skill
  2. Override the class-level fields
  3. Implement run(**kwargs) -> str

Example:
    @dataclass
    class MySkill(Skill):
        name        : str       = "my_skill"
        description : str       = "does something useful"
        examples    : list[str] = field(default_factory=lambda: [
            "do the thing",
            "activate my skill",
        ])
        category    : str       = "other"

        def run(self, query: str = "", **kwargs) -> str:
            return "did the thing."
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Skill(ABC):
    """
    Abstract base dataclass for all Kiki skills.
    Subclass this, override fields, implement run().
    """
    name:            str            = ""
    description:     str            = ""
    examples:        list[str]      = field(default_factory=list)
    category:        str            = "other"
    parameters:      dict[str, str] = field(default_factory=dict)
    requires_vision: bool           = False

    @abstractmethod
    def run(self, **kwargs) -> str:
        """
        Execute the skill. Always returns a string — kiki's response.
        kwargs contains at minimum:
            query    : str             — raw user message
            registry : Registry | None — for skills that need introspection
        Vision skills also receive:
            screenshot : str           — base64 JPEG
        """
        ...

    @property
    def corpus(self) -> str:
        """Text embedded to represent this skill in the vector search."""
        return " ".join([self.description] + self.examples)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"category={self.category!r}, "
            f"examples={len(self.examples)})"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # cannot instantiate abstract base
    try:
        Skill()
        assert False, "should have raised TypeError"
    except TypeError:
        pass

    # concrete subclass without run() also fails
    @dataclass
    class BadSkill(Skill):
        name: str = "bad"

    try:
        BadSkill()
        assert False, "should have raised TypeError"
    except TypeError:
        pass

    # correct subclass works
    @dataclass
    class GoodSkill(Skill):
        name:        str       = "good"
        description: str       = "does something good"
        examples:    list[str] = field(default_factory=lambda: [
            "do the good thing",
            "activate good skill",
        ])
        category:    str       = "other"

        def run(self, query: str = "", **kwargs) -> str:
            return "did the good thing."

    skill = GoodSkill()
    assert skill.name        == "good"
    assert skill.category    == "other"
    assert skill.corpus      == "does something good do the good thing activate good skill"
    assert skill.run()       == "did the good thing."
    assert "GoodSkill"       in repr(skill)

    # fields are independent between instances
    s1 = GoodSkill()
    s2 = GoodSkill()
    s1.examples.append("extra")
    assert "extra" not in s2.examples, "mutable default leaked between instances"

    print("base.py — all tests passed.")
    print(repr(skill))