"""Build short AFL fact cards from the dataset for optional semantic retrieval."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import FACT_CARDS
from .data_access import load_matches, load_players_info


def build_fact_cards(path: Path | None = None) -> Path:
    """
    Short club/player blurbs built from real tables (not news).
    Good for background search; exact numbers still come from structured tools.
    """
    path = path or FACT_CARDS
    path.parent.mkdir(parents=True, exist_ok=True)
    m = load_matches()
    info = load_players_info()
    lines: list[str] = []

    for team, g in m.groupby("home_team"):
        years = f"{int(g['year'].min())}-{int(g['year'].max())}"
        home_wr = g["home_win"].mean()
        venues = g["venue"].value_counts().head(2)
        venue_txt = ", ".join(f"{v} ({c})" for v, c in venues.items())
        lines.append(
            f"Club card: {team}. Appears as home team in dataset years {years}. "
            f"Home win rate in those home games: {home_wr:.1%}. "
            f"Common home venues: {venue_txt}. "
            f"Ask structured tools for exact H2H records or recent scores."
        )

    for _, r in info.nlargest(30, "last_age").iterrows():
        lines.append(
            f"Player card: {r['player_name']} (id {r['player_id']}). "
            f"Debut {r.get('debut_date')}, last listed {r.get('last_date')}. "
            f"Teams field: {r.get('player_teams')}. "
            f"Height {r.get('height')} cm, weight {r.get('weight')} kg. "
            f"Use season/game tools for exact disposals and goals."
        )

    uniq = list(dict.fromkeys(lines))
    path.write_text("\n\n".join(uniq), encoding="utf-8")
    return path


def load_fact_documents() -> list[str]:
    if not FACT_CARDS.exists():
        build_fact_cards()
    text = FACT_CARDS.read_text(encoding="utf-8")
    docs = [d.strip() for d in text.split("\n\n") if d.strip()]
    return docs
