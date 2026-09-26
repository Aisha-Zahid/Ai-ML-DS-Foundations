"""Document loading and chunking for semantic RAG."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import SEMANTIC


@dataclass
class Document:
    doc_id: str
    source: str
    text: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source: str
    text: str
    chunk_index: int


def load_documents(root: Path | None = None) -> list[Document]:
    base = root or SEMANTIC
    docs: list[Document] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        rel = str(path.relative_to(base)).replace("\\", "/")
        docs.append(Document(doc_id=rel, source=rel, text=text))
    return docs


def chunk_text(text: str, chunk_size: int, overlap: int = 80) -> list[str]:
    """Split on paragraphs first, then pack to chunk_size with overlap."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paras:
        paras = [text]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= chunk_size:
            buf = f"{buf}\n\n{p}"
        else:
            chunks.append(buf)
            # overlap tail
            tail = buf[-overlap:] if overlap and len(buf) > overlap else buf
            buf = f"{tail}\n\n{p}" if tail else p
            while len(buf) > chunk_size * 2:
                chunks.append(buf[:chunk_size])
                buf = buf[chunk_size - overlap :]
    if buf:
        chunks.append(buf)
    # hard-split any oversized chunk
    final: list[str] = []
    for c in chunks:
        if len(c) <= chunk_size:
            final.append(c)
        else:
            start = 0
            while start < len(c):
                end = min(start + chunk_size, len(c))
                final.append(c[start:end])
                if end >= len(c):
                    break
                start = max(0, end - overlap)
    return final


def chunk_documents(docs: list[Document], chunk_size: int, overlap: int = 80) -> list[Chunk]:
    out: list[Chunk] = []
    for doc in docs:
        parts = chunk_text(doc.text, chunk_size=chunk_size, overlap=overlap)
        for i, part in enumerate(parts):
            out.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}:::{i}",
                    doc_id=doc.doc_id,
                    source=doc.source,
                    text=part,
                    chunk_index=i,
                )
            )
    return out
