"""Call Day-2 prediction + Day-3 retrieval from Day-4 nodes."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any

from .config import DAY2, DAY3

_CACHE: dict[str, Any] = {}


def _load_day3_data_access():
    """Load Day-3 data_access without clashing with Day-4's `src` package."""
    if "day3_da" in _CACHE:
        return _CACHE["day3_da"]

    pkg_name = "day3src"
    src_dir = DAY3 / "src"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(src_dir)]
        sys.modules[pkg_name] = pkg

    def _sub(mod_name: str):
        full = f"{pkg_name}.{mod_name}"
        if full in sys.modules:
            return sys.modules[full]
        path = src_dir / f"{mod_name}.py"
        spec = importlib.util.spec_from_file_location(
            full,
            path,
            submodule_search_locations=[str(src_dir)],
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    _sub("config")
    da = _sub("data_access")
    _CACHE["day3_da"] = da
    return da


def _day2_predict():
    if "day2_predict" in _CACHE:
        return _CACHE["day2_predict"]
    path = DAY2 / "predict.py"
    # Ensure Day-2 cwd-style imports (joblib models relative to DAY2)
    if str(DAY2) not in sys.path:
        sys.path.insert(0, str(DAY2))
    spec = importlib.util.spec_from_file_location("day2_predict_mod", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    _CACHE["day2_predict"] = mod
    return mod


def predict_match(team_a: str, team_b: str, date: str, home_team: str | None = None) -> dict:
    return _day2_predict().predict_match_winner(team_a, team_b, date, home_team=home_team)


def predict_top(team: str, match_date: str, opponent: str | None = None, top_k: int = 5) -> dict:
    return _day2_predict().predict_top_player(
        team=team, match_date=match_date, opponent=opponent, top_k=top_k
    )


def retrieve_h2h(team_a: str, team_b: str, since_year: int | None = None) -> dict:
    return _load_day3_data_access().team_h2h_record(team_a, team_b, since_year=since_year)


def retrieve_recent(team: str, n: int = 5) -> dict:
    return _load_day3_data_access().recent_team_results(team, n=n)


def retrieve_player_season(player: str, year: int, team: str | None = None) -> dict:
    return _load_day3_data_access().player_season_stats(player, year, team=team)


def retrieve_player_game(
    player: str, match_date: str | None = None, year: int | None = None
) -> dict:
    return _load_day3_data_access().player_game_stats(
        player, match_date=match_date, year=year
    )


def tool_ok(result: Any) -> bool:
    if result is None:
        return False
    if isinstance(result, dict) and result.get("error"):
        return False
    if isinstance(result, dict) and result.get("games") == 0:
        return False
    return True


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
