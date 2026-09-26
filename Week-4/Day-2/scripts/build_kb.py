"""Build SQLite + TF-IDF vector indexes for all chunk variants."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.chunking import chunk_documents, load_documents  # noqa: E402
from src.config import CHUNK_VARIANTS, DEFAULT_CHUNK, PROCESSED, RESULTS  # noqa: E402
from src.db import build_sqlite  # noqa: E402
from src.rag import build_variant  # noqa: E402


def main() -> None:
    # ensure seed data exists
    seed = ROOT / "scripts" / "seed_kb.py"
    if not (ROOT / "data" / "structured" / "properties.csv").exists():
        import runpy

        runpy.run_path(str(seed), run_name="__main__")

    db = build_sqlite()
    print(f"SQLite -> {db}")

    stats = {}
    docs = load_documents()
    for name, size in CHUNK_VARIANTS.items():
        chunks = chunk_documents(docs, chunk_size=size)
        out = build_variant(name)
        stats[name] = {
            "chunk_size": size,
            "n_docs": len(docs),
            "n_chunks": len(chunks),
            "avg_chunk_chars": round(sum(len(c.text) for c in chunks) / max(len(chunks), 1), 1),
            "index_dir": str(out),
        }
        print(f"Indexed {name}: {stats[name]['n_chunks']} chunks -> {out}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "index_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    (PROCESSED / "build_ok.txt").write_text(
        f"default_chunk={DEFAULT_CHUNK}\nvariants={list(CHUNK_VARIANTS)}\n",
        encoding="utf-8",
    )
    print("Done.")


if __name__ == "__main__":
    main()
