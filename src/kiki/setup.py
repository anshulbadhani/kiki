"""
kiki setup — run once before first launch.
Downloads paraphrase-MiniLM-L3-v2 ONNX model to the platform-specific
kiki data directory. After this runs, kiki works fully offline.

Usage:
    uv run python -m kiki.setup
    
# normal first-time setup
uv run python -m kiki.setup

# check if model is already downloaded
uv run python -m kiki.setup --verify

# force re-download if something is corrupted
uv run python -m kiki.setup --force
"""
from __future__ import annotations
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Platform-specific kiki home
# ---------------------------------------------------------------------------

def kiki_home() -> Path:
    if sys.platform == "win32":
        import os
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "kiki"
    path.mkdir(parents=True, exist_ok=True)
    return path


MODELS_DIR = kiki_home() / "models"


# ---------------------------------------------------------------------------
# Model spec
# ---------------------------------------------------------------------------

MODEL_REPO   = "sentence-transformers/paraphrase-MiniLM-L3-v2"
MODEL_FILES  = [
    "onnx/model.onnx",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
]


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_model(force: bool = False) -> None:
    model_file = MODELS_DIR / "onnx" / "model.onnx"

    if model_file.exists() and not force:
        print(f"[kiki] model already exists at {MODELS_DIR}")
        print("[kiki] run with --force to re-download")
        return

    print("[kiki] downloading paraphrase-MiniLM-L3-v2 (~17MB, one time only)...")
    print(f"[kiki] saving to {MODELS_DIR}")

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print(
            "[kiki] huggingface-hub not found.\n"
            "       install it temporarily with: pip install huggingface-hub\n"
            "       or: uv add --dev huggingface-hub"
        )
        sys.exit(1)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for filename in MODEL_FILES:
        dest = MODELS_DIR / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists() and not force:
            print(f"  [skip] {filename}")
            continue

        print(f"  [download] {filename}")
        try:
            hf_hub_download(
                repo_id   = MODEL_REPO,
                filename  = filename,
                local_dir = MODELS_DIR,
            )
        except Exception as e:
            print(f"  [error] failed to download {filename}: {e}")
            sys.exit(1)

    print("[kiki] model ready. kiki can now route skills offline.")


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def verify_model() -> bool:
    """Check all required files exist. Returns True if model is ready."""
    missing = []
    for filename in MODEL_FILES:
        path = MODELS_DIR / filename
        if not path.exists():
            missing.append(filename)

    if missing:
        print("[kiki] missing model files:")
        for f in missing:
            print(f"  - {f}")
        print("[kiki] run: uv run python -m kiki.setup")
        return False

    return True


def verify_and_exit() -> None:
    if verify_model():
        print(f"[kiki] all model files present at {MODELS_DIR}")
    else:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    if "--verify" in args:
        verify_and_exit()
        return

    force = "--force" in args
    download_model(force=force)


if __name__ == "__main__":
    main()