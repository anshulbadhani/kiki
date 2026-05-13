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
from pathlib import Path
from dataclasses import dataclass, field

from kiki.skills.encoder import Encoder
from kiki.skills.base import Skill
from kiki.config import SKILL_THRESHOLD


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
        self._load_external()

    # -----------------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------------

    # Good for testing but fails while shipping. Keeping it for fast prototyping while adding new in-built skills
    # def _load_all(self) -> None:
    #     pkg_path = [str(Path(__file__).parent)]
    #     pkg_name = __package__

    #     for finder, module_name, _ in pkgutil.iter_modules(pkg_path):
    #         if module_name in ("registry", "encoder", "base"):
    #             continue

    #         full_name = f"{pkg_name}.{module_name}"
    #         print(f"[registry] scanning: {module_name}")
    #         try:
    #             mod = importlib.import_module(full_name)
    #         except Exception as e:
    #             print(f"[registry] failed to load {module_name}: {e}")
    #             continue

    #         for attr_name in dir(mod):
    #             attr = getattr(mod, attr_name)
    #             if (
    #                 isinstance(attr, type)
    #                 and issubclass(attr, Skill)
    #                 and attr is not Skill
    #             ):
    #                 try:
    #                     instance        = attr()
    #                     instance.vector = self._encoder.encode(instance.corpus)
    #                     self._skills[instance.name] = instance
    #                     print(f"[registry] loaded skill: {instance.name}")
    #                 except Exception as e:
    #                     print(f"[registry] failed to instantiate {attr_name}: {e}")
    
    def _load_all(self) -> None:
        """Loads Kiki's core built-in skills."""
        # 1. Explicitly import the built-in modules
        from . import (
            clipboard, 
            help, 
            notify, 
            screenshot, 
            show_skills, 
            web_search
        )
        
        # 2. Put them in a list
        core_modules = [
            clipboard, help, notify, screenshot, show_skills, web_search
        ]

        # 3. Load them exactly like we load external skills
        for mod in core_modules:
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Skill)
                    and attr is not Skill
                ):
                    instance        = attr()
                    instance.vector = self._encoder.encode(instance.corpus)
                    self._skills[instance.name] = instance
                    print(f"[registry] loaded built-in skill: {instance.name}")

    # -----------------------------------------------------------------------
    # Custom Skills Support (CSS 🦅)
    # -----------------------------------------------------------------------

    def _load_external(self) -> None:
        """Dynamically loads raw .py files from the user's local AppData folder."""
        import sys
        import importlib.util
        from ..paths import user_skills_dir
        
        skills_dir = user_skills_dir()
        print(f"[registry] scanning external folder: {skills_dir}")

        for py_file in skills_dir.glob("*.py"):
            if py_file.stem.startswith("_"):
                continue

            print(f"[registry] loading custom skill: {py_file.name}")
            try:
                # 1. Create a safe, unique module name
                module_name = f"kiki.custom.{py_file.stem}"
                
                # 2. Load the spec
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    
                    # 3. THE MAGIC FIX: Register it globally BEFORE executing!
                    sys.modules[module_name] = mod 
                    
                    # 4. Now it is safe to execute
                    spec.loader.exec_module(mod)

                    # Scan the loaded module for Skill subclasses
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, Skill)
                            and attr is not Skill
                        ):
                            instance        = attr()
                            instance.vector = self._encoder.encode(instance.corpus)
                            self._skills[instance.name] = instance
                            print(f"[registry] successfully loaded external skill: {instance.name}")

            except Exception as e:
                print(f"[registry] failed to load external skill {py_file.name}: {e}")
                                
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

    def make_skill(target_mod):
        class ConcreteSkill(Skill):
            def run(self, **kwargs) -> str:
                # This now correctly points to the captured target_mod
                return target_mod.run(**kwargs)
        
        return ConcreteSkill(
            name            = target_mod.NAME,
            description     = target_mod.DESCRIPTION,
            examples        = target_mod.EXAMPLES,
            parameters      = target_mod.PARAMETERS,
            requires_vision = False,
        )

    for mod in (stub_open, stub_search):
        skill = make_skill(mod)
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