"""Week 4 Day 2 paths and defaults."""

from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1]
DATA = DAY2 / "data"
STRUCTURED = DATA / "structured"
SEMANTIC = DATA / "semantic"
PROCESSED = DATA / "processed"
VECTORSTORE = DAY2 / "vectorstore"
RESULTS = DAY2 / "results"
DOCS = DAY2 / "docs"

SQLITE_PATH = PROCESSED / "realestate_hub.sqlite"
FAISS_DIR = VECTORSTORE / "faiss_tfidf"

# Chunking variants to evaluate (chars approx; split on paragraphs then size)
CHUNK_VARIANTS = {
    "small_400": 400,
    "medium_800": 800,
    "large_1200": 1200,
}
DEFAULT_CHUNK = "medium_800"
TOP_K = 4
