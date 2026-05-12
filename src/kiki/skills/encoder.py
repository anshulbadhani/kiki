"""
Local semantic encoder using paraphrase-MiniLM-L3-v2 (ONNX).
Zero network calls at runtime — model loaded from ~/.kiki/models (or platform equivalent).

Usage:
    encoder = Encoder()
    vec  = encoder.encode("open chrome")
    sim  = encoder.cosine(vec, other_vec)
"""
from __future__ import annotations
import sys
import numpy as np
from pathlib import Path

from ..config import SKILL_THRESHOLD


# ---------------------------------------------------------------------------
# Platform path (mirrors setup.py — no import to avoid circular deps)
# ---------------------------------------------------------------------------

def _kiki_home() -> Path:
    if sys.platform == "win32":
        import os
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME",
                                   Path.home() / ".local" / "share"))
    return base / "kiki"


DEFAULT_MODEL_DIR = _kiki_home() / "models"


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

class Encoder:
    """
    Wraps the ONNX inference session and HF fast tokenizer.
    Thread-safe for read (encode) after construction.
    """

    def __init__(self, model_dir: Path = DEFAULT_MODEL_DIR) -> None:
        self._model_dir = model_dir
        self._session   = self._load_session()
        self._tokenizer = self._load_tokenizer()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def encode(self, text: str) -> np.ndarray:
        """
        Encode a string into a unit-normalised embedding vector.
        Returns shape (hidden_size,) float32 ndarray.
        """
        enc            = self._tokenizer.encode(text)
        input_ids      = np.array([enc.ids],            dtype=np.int64)
        attention_mask = np.array([enc.attention_mask], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)

        outputs = self._session.run(None, {
            "input_ids":      input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        })

        # outputs[0] shape: (1, seq_len, hidden_size)
        pooled = self._mean_pool(outputs[0], attention_mask)
        return self._normalise(pooled)

    def encode_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Encode multiple texts. Returns list of unit-normalised vectors."""
        return [self.encode(t) for t in texts]

    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Cosine similarity between two unit-normalised vectors.
        Both must come from encode() — already normalised, so just dot product.
        """
        return float(np.dot(a, b))

    def best_match(
        self,
        query: np.ndarray,
        candidates: list[tuple[str, np.ndarray]],
        threshold: float = SKILL_THRESHOLD,
    ) -> tuple[str, float] | tuple[None, float]:
        """
        Find the best matching candidate above threshold.
        candidates: list of (name, vector) pairs
        Returns (name, score) or (None, best_score) if nothing clears threshold.
        """
        if not candidates:
            return None, 0.0

        scores = [(name, self.cosine(query, vec)) for name, vec in candidates]
        best_name, best_score = max(scores, key=lambda x: x[1])

        if best_score >= threshold:
            return best_name, best_score
        return None, best_score

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------

    def _load_session(self):
        try:
            import onnxruntime as ort
        except ImportError:
            raise RuntimeError(
                "onnxruntime not installed. Run: uv add onnxruntime"
            )

        model_path = self._model_dir / "onnx" / "model.onnx"
        if not model_path.exists():
            raise FileNotFoundError(
                f"ONNX model not found at {model_path}\n"
                "Run: uv run python -m kiki.setup"
            )

        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 2
        opts.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        return ort.InferenceSession(
            str(model_path),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )

    def _load_tokenizer(self):
        try:
            from tokenizers import Tokenizer
        except ImportError:
            raise RuntimeError(
                "tokenizers not installed. Run: uv add tokenizers"
            )

        tokenizer_path = self._model_dir / "tokenizer.json"
        if not tokenizer_path.exists():
            raise FileNotFoundError(
                f"Tokenizer not found at {tokenizer_path}\n"
                "Run: uv run python -m kiki.setup"
            )

        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        tokenizer.enable_truncation(max_length=128)
        tokenizer.enable_padding(length=128)
        return tokenizer

    @staticmethod
    def _mean_pool(
        hidden:  np.ndarray,   # (1, seq_len, hidden_size)
        mask:    np.ndarray,   # (1, seq_len)
    ) -> np.ndarray:           # (hidden_size,)
        mask_f = mask[0].astype(np.float32)              # (seq_len,)
        vecs   = hidden[0]                               # (seq_len, hidden_size)
        summed = (vecs * mask_f[:, None]).sum(axis=0)
        count  = mask_f.sum().clip(min=1e-9)
        return summed / count

    @staticmethod
    def _normalise(vec: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 1e-9 else vec


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from kiki.setup import verify_model
    if not verify_model():
        sys.exit(1)

    enc = Encoder()

    # encode returns a unit vector
    v = enc.encode("open chrome")
    assert v.shape == (384,), f"unexpected shape {v.shape}"
    assert abs(np.linalg.norm(v) - 1.0) < 1e-5, "vector not normalised"

    # identical texts → similarity ~1.0
    v1 = enc.encode("open chrome")
    v2 = enc.encode("open chrome")
    assert enc.cosine(v1, v2) > 0.999

    # semantically similar → high similarity
    v3 = enc.encode("launch google chrome")
    sim_close = enc.cosine(v1, v3)
    assert sim_close > 0.7, f"expected >0.7 for similar phrases, got {sim_close:.3f}"

    # semantically different → low similarity
    v4 = enc.encode("what is the weather today")
    sim_far = enc.cosine(v1, v4)
    assert sim_far < 0.6, f"expected <0.6 for different phrases, got {sim_far:.3f}"

    # best_match
    candidates = [
        ("open_app",   enc.encode("open launch start an application program app spotify chrome")),
        ("web_search", enc.encode("search find look up browse google information recipe news weather")),
        ("clipboard",  enc.encode("copy paste clipboard text")),
    ]
    
    for name, vec in candidates:
        print(f"  {name}: {enc.cosine(enc.encode('find me a recipe'), vec):.4f}")
    
    name, score = enc.best_match(enc.encode("launch spotify"), candidates)
    assert name == "open_app", f"expected open_app, got {name} ({score:.3f})"

    for name, vec in candidates:
        print(f"  {name}: {enc.cosine(enc.encode('launch spotify'), vec):.4f}")
    
    name, score = enc.best_match(enc.encode("find me a recipe"), candidates)
    assert name == "web_search", f"expected web_search, got {name} ({score:.3f})"

    # below threshold → None
    name, score = enc.best_match(
        enc.encode("xyzzy nonsense gibberish"),
        candidates,
        threshold=0.99,
    )
    assert name is None

    print(f"encoder.py — all tests passed.")
    print(f"  similar pair score : {sim_close:.4f}")
    print(f"  different pair score: {sim_far:.4f}")