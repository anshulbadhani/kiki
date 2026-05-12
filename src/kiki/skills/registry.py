"""
Skill registry — scans skills/, builds embeddings at startup, routes queries.

Each skill module must define:
    NAME        : str          — unique identifier
    DESCRIPTION : str          — what the skill does
    EXAMPLES    : list[str]    — example user phrases (6-8 recommended)
    PARAMETERS  : dict         — {param_name: description} or {}
    run(**kwargs) -> str       — executes the skill, returns kiki's response

Optional:
    REQUIRES_VISION : bool     — True if skill needs a screenshot
"""
from __future__ import annotations
import importlib
import pkgutil
import sys
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np

from .encoder import Encoder
from .base import Skill
from ..config import SKILL_THRESHOLD


# # ---------------------------------------------------------------------------
# # Skill descriptor
# # ---------------------------------------------------------------------------

# @dataclass
# class Skill:
#     name:            str
#     description:     str
#     examples:        list[str]
#     parameters:      dict[str, str]
#     requires_vision: bool
#     run:             callable
#     vector:          np.ndarray = field(default=None, repr=False)

#     @property
#     def corpus(self) -> str:
#         """Text we embed to represent this skill."""
#         return " ".join([self.description] + self.examples)


# # ---------------------------------------------------------------------------
# # Registry
# # ---------------------------------------------------------------------------

class Registry:
    """
    Loads all skills from the skills/ package, embeds them,
    and routes user queries to the best match.
    """

    def __init__(self, encoder: Encoder) -> None:
        self._encoder: Encoder         = encoder
        self._skills:  dict[str, Skill] = {}
        self._load_all()

    # -----------------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------------

    def _load_all(self) -> None:
        pkg_path = [str(Path(__file__).parent)]
        pkg_name = __package__

        for finder, module_name, _ in pkgutil.iter_modules(pkg_path):
            if module_name in ("registry", "encoder", "base"):
                continue

            full_name = f"{pkg_name}.{module_name}"
            print(f"[registry] scanning: {module_name}")
            try:
                mod = importlib.import_module(full_name)
            except Exception as e:
                print(f"[registry] failed to load {module_name}: {e}")
                continue

            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Skill)
                    and attr is not Skill
                ):
                    try:
                        instance        = attr()
                        instance.vector = self._encoder.encode(instance.corpus)
                        self._skills[instance.name] = instance
                        print(f"[registry] loaded skill: {instance.name}")
                    except Exception as e:
                        print(f"[registry] failed to instantiate {attr_name}: {e}")

    # -----------------------------------------------------------------------
    # Routing
    # -----------------------------------------------------------------------

    def route(self, message: str, screenshot=None, threshold: float = SKILL_THRESHOLD) -> str | None:
        if not self._skills:
            return None

        query = self._encoder.encode(message)
        candidates = [
            (name, skill.vector)
            for name, skill in self._skills.items()
            if not skill.requires_vision or screenshot is not None
        ]

        best_name, score = self._encoder.best_match(query, candidates, threshold)
        if best_name is None:
            return None

        skill = self._skills[best_name]
        print(f"[registry] matched '{best_name}' (score={score:.3f})")

        try:
            kwargs = {"query": message, "registry": self}
            if skill.requires_vision:
                kwargs["screenshot"] = screenshot
            return skill.run(**kwargs)
        except Exception as e:
            print(f"[registry] skill '{best_name}' failed: {e}")
            return None

    def _extract_args(self, message: str, skill: Skill) -> dict:
        """
        Naive arg extraction — passes raw message as 'query' if skill
        expects it. Skills that need structured args do their own parsing.
        """
        if not skill.parameters:
            return {}
        if "query" in skill.parameters:
            return {"query": message}
        if "text" in skill.parameters:
            return {"text": message}
        return {}

    # -----------------------------------------------------------------------
    # Introspection (for help skill + skill graph)
    # -----------------------------------------------------------------------

    def all_skills(self) -> list[Skill]:
        return list(self._skills.values())

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def __len__(self) -> int:
        return len(self._skills)

    def __repr__(self) -> str:
        return f"Registry({list(self._skills.keys())})"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # minimal stub skills for testing — no real skill files needed
    import types

    def _make_skill_mod(name, description, examples, run_fn):
        mod             = types.ModuleType(name)
        mod.NAME        = name
        mod.DESCRIPTION = description
        mod.EXAMPLES    = examples
        mod.PARAMETERS  = {"query": "user message"}
        mod.run         = run_fn
        return mod

    # patch importlib so _load_all picks up our stubs
    stub_open = _make_skill_mod(
        "open_app",
        "open launch start an application program",
        ["open chrome", "launch spotify", "start notepad", "open an app"],
        lambda **kw: f"opening {kw.get('query', '')}.",
    )
    stub_search = _make_skill_mod(
        "web_search",
        "search find look up browse information on the web internet google",
        [
            "search for recipes",
            "find me a pasta recipe",
            "look up the news",
            "find information about python",
            "google something",
            "search the web",
            "what is the recipe for",
            "find me information about",
        ],
        lambda **kw: f"searching for {kw.get('query', '')}.",
    )

    enc      = Encoder()
    registry = Registry.__new__(Registry)
    registry._encoder = enc
    registry._skills  = {}

    for mod in (stub_open, stub_search):
        skill        = Skill(
            name            = mod.NAME,
            description     = mod.DESCRIPTION,
            examples        = mod.EXAMPLES,
            parameters      = mod.PARAMETERS,
            requires_vision = False,
            run             = mod.run,
        )
        skill.vector = enc.encode(skill.corpus)
        registry._skills[skill.name] = skill

    # route open
    result = registry.route("launch spotify")
    assert result is not None,          "expected a match for 'launch spotify'"
    assert "opening" in result,         f"unexpected result: {result}"

    # route search
    result = registry.route("find me a pasta recipe")
    print(f"web_search score: {enc.cosine(enc.encode('find me a pasta recipe'), registry._skills['web_search'].vector):.4f}")
    assert result is not None,          "expected a match for 'find me a pasta recipe'"
    assert "searching" in result,       f"unexpected result: {result}"

    # no match → None
    result = registry.route("xyzzy gibberish nonsense", threshold=0.99)
    assert result is None,              "expected None for gibberish"

    # introspection
    assert len(registry) == 2
    assert registry.get("open_app") is not None

    print("registry.py — all tests passed.")
    print(repr(registry))