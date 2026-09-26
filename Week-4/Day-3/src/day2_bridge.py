"""Load Day-2 KB modules without clashing with Day-3 `src`."""

from __future__ import annotations

import importlib.util
import sys
import types
from typing import Any

from .config import DAY2

_CACHE: dict[str, Any] = {}


def load_day2() -> dict[str, Any]:
    if "day2" in _CACHE:
        return _CACHE["day2"]

    pkg = "day2src"
    src_dir = DAY2 / "src"
    if pkg not in sys.modules:
        m = types.ModuleType(pkg)
        m.__path__ = [str(src_dir)]
        sys.modules[pkg] = m

    def _sub(name: str):
        full = f"{pkg}.{name}"
        if full in sys.modules:
            return sys.modules[full]
        path = src_dir / f"{name}.py"
        spec = importlib.util.spec_from_file_location(
            full, path, submodule_search_locations=[str(src_dir)]
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    for name in (
        "config",
        "db",
        "chunking",
        "rag",
        "structured",
        "recommend",
        "answer",
    ):
        _sub(name)

    # Ensure SQLite + default index exist
    db = sys.modules[f"{pkg}.db"]
    rag = sys.modules[f"{pkg}.rag"]
    cfg = sys.modules[f"{pkg}.config"]
    if not cfg.SQLITE_PATH.exists():
        # seed + build if needed
        import runpy

        seed = DAY2 / "scripts" / "seed_kb.py"
        if seed.exists() and not (DAY2 / "data" / "structured" / "properties.csv").exists():
            runpy.run_path(str(seed), run_name="__main__")
        db.build_sqlite()
    if not cfg.FAISS_DIR.exists():
        try:
            rag.build_variant(cfg.DEFAULT_CHUNK)
        except Exception:
            db.build_sqlite()
            rag.build_variant(cfg.DEFAULT_CHUNK)

    bundle = {
        "recommend": sys.modules[f"{pkg}.recommend"].recommend,
        "answer_question": sys.modules[f"{pkg}.answer"].answer_question,
        "retrieve": sys.modules[f"{pkg}.rag"].retrieve,
        "search_properties": sys.modules[f"{pkg}.structured"].search_properties,
        "parse_crore": sys.modules[f"{pkg}.recommend"].parse_crore_to_pkr,
    }
    _CACHE["day2"] = bundle
    return bundle
