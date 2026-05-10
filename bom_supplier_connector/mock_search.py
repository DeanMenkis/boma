"""
Mock catalog search when DigiKey is unavailable or returns no candidates.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_CATALOG: list[dict] | None = None


def _catalog_path() -> Path:
    return Path(__file__).resolve().parent / "mock_catalog.json"


def load_mock_catalog() -> list[dict]:
    global _CATALOG
    if _CATALOG is None:
        with open(_catalog_path(), encoding="utf-8") as f:
            _CATALOG = json.load(f)
    return _CATALOG


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def _tokens(s: str) -> set[str]:
    parts = re.split(r"[^\w.µΩ]+", _norm(s), flags=re.IGNORECASE)
    return {p for p in parts if len(p) > 1}


def mock_keyword_search(query: str, quantity: int) -> list[dict]:
    """Score mock entries by overlap with query / keywords / MPN."""
    cat = load_mock_catalog()
    q = _norm(query)
    qt = _tokens(query)
    scored: list[tuple[float, dict]] = []
    for entry in cat:
        blob = " ".join(
            [
                entry.get("mpn", ""),
                entry.get("description", ""),
                " ".join(entry.get("keywords", [])),
            ]
        )
        bt = _tokens(blob)
        overlap = len(qt & bt)
        if q and q in _norm(blob):
            overlap += 5
        for kw in entry.get("keywords", []):
            if _norm(kw) in q or q in _norm(kw):
                overlap += 3
        if overlap > 0:
            scored.append((float(overlap), dict(entry)))
    scored.sort(key=lambda x: -x[0])
    out = []
    for _, e in scored[:8]:
        row = {k: v for k, v in e.items() if k != "keywords"}
        row.setdefault("unit_price", float(row.get("unit_price", 0)))
        row.setdefault("stock", int(row.get("stock", 0)))
        row.setdefault("lead_time_weeks", float(row.get("lead_time_weeks", 0)))
        out.append(row)
    return out


def mock_partnumber_search(part_number: str, quantity: int) -> list[dict]:
    pn = part_number.strip()
    if not pn:
        return []
    cat = load_mock_catalog()
    pn_l = pn.lower()
    for entry in cat:
        mpn = (entry.get("mpn") or "").lower()
        dk = (entry.get("digikey_part_number") or "").lower()
        if pn_l == mpn or pn_l == dk or pn_l in mpn or mpn in pn_l:
            row = {k: v for k, v in entry.items() if k != "keywords"}
            return [row]
    # partial keyword match on MPN-like strings
    hits = mock_keyword_search(part_number, quantity)
    return hits[:1]


def merge_mock_if_empty(row: dict, candidates: list[dict]) -> list[dict]:
    if candidates:
        return candidates
    # Row-aware broad query
    parts = [
        str(row.get("name") or ""),
        str(row.get("footprint") or ""),
        str(row.get("mpn") or ""),
        str(row.get("supplier_part") or ""),
    ]
    q = " ".join(p for p in parts if p)
    return mock_keyword_search(q, int(row.get("quantity") or 1))
