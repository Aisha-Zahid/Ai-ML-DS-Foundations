"""TF-IDF vector store (local, no API). Swap for Chroma/OpenAI embeddings later."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .chunking import Chunk, chunk_documents, load_documents
from .config import DEFAULT_CHUNK, CHUNK_VARIANTS, FAISS_DIR, TOP_K, VECTORSTORE


class TfidfStore:
    def __init__(self) -> None:
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix: Any = None
        self.chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        texts = [c.text for c in chunks]
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=20000,
            stop_words=None,
        )
        self.matrix = self.vectorizer.fit_transform(texts)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        assert self.vectorizer is not None and self.matrix is not None
        with (directory / "vectorizer.pkl").open("wb") as f:
            pickle.dump(self.vectorizer, f)
        with (directory / "matrix.pkl").open("wb") as f:
            pickle.dump(self.matrix, f)
        meta = [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "source": c.source,
                "chunk_index": c.chunk_index,
                "text": c.text,
            }
            for c in self.chunks
        ]
        (directory / "chunks.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load(self, directory: Path) -> None:
        with (directory / "vectorizer.pkl").open("rb") as f:
            self.vectorizer = pickle.load(f)
        with (directory / "matrix.pkl").open("rb") as f:
            self.matrix = pickle.load(f)
        meta = json.loads((directory / "chunks.json").read_text(encoding="utf-8"))
        self.chunks = [
            Chunk(
                chunk_id=m["chunk_id"],
                doc_id=m["doc_id"],
                source=m["source"],
                text=m["text"],
                chunk_index=m["chunk_index"],
            )
            for m in meta
        ]

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        if not self.vectorizer or self.matrix is None or not self.chunks:
            return []
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix).ravel()
        idx = np.argsort(-sims)[:top_k]
        out = []
        for i in idx:
            score = float(sims[i])
            if score <= 0:
                continue
            c = self.chunks[int(i)]
            out.append(
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "source": c.source,
                    "score": round(score, 4),
                    "text": c.text,
                }
            )
        return out


def build_variant(variant: str = DEFAULT_CHUNK) -> Path:
    size = CHUNK_VARIANTS[variant]
    docs = load_documents()
    chunks = chunk_documents(docs, chunk_size=size)
    store = TfidfStore()
    store.build(chunks)
    out_dir = VECTORSTORE / f"tfidf_{variant}"
    store.save(out_dir)
    # also write default alias for medium
    if variant == DEFAULT_CHUNK:
        FAISS_DIR.parent.mkdir(parents=True, exist_ok=True)
        store.save(FAISS_DIR)
    return out_dir


def get_default_store() -> TfidfStore:
    store = TfidfStore()
    path = FAISS_DIR if FAISS_DIR.exists() else VECTORSTORE / f"tfidf_{DEFAULT_CHUNK}"
    if not path.exists():
        build_variant(DEFAULT_CHUNK)
        path = FAISS_DIR
    store.load(path)
    return store


def retrieve(query: str, top_k: int = TOP_K, store: TfidfStore | None = None) -> list[dict]:
    s = store or get_default_store()
    return s.search(query, top_k=top_k)
