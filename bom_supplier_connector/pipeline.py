"""
BOM CSV parsing and enrich_bom main pipeline.
"""
from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .agents import orchestrator_agent, specialist_agent
from .mock_search import merge_mock_if_empty


def parse_bom_csv(filepath: str) -> list[dict]:
    path = Path(filepath)
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows: list[dict] = []
        for raw in reader:
            try:
                rid = int((raw.get("ID") or raw.get("id") or "0").strip())
            except (TypeError, ValueError, AttributeError):
                rid = len(rows) + 1
            try:
                qty = int(float((raw.get("Quantity") or "0").strip()))
            except (TypeError, ValueError, AttributeError):
                qty = 0
            try:
                price = float((raw.get("Price") or "0").strip())
            except (TypeError, ValueError, AttributeError):
                price = 0.0
            rows.append(
                {
                    "id": rid,
                    "name": (raw.get("Name") or "").strip(),
                    "designator": (raw.get("Designator") or "").strip(),
                    "footprint": (raw.get("Footprint") or "").strip(),
                    "quantity": qty,
                    "mpn": (raw.get("Manufacturer Part") or "").strip(),
                    "manufacturer": (raw.get("Manufacturer") or "").strip(),
                    "supplier": (raw.get("Supplier") or "").strip(),
                    "supplier_part": (raw.get("Supplier Part") or "").strip(),
                    "existing_price": price,
                }
            )
        return rows


def _apply_mock_fallback(orch: list[dict]) -> list[dict]:
    merged: list[dict[str, Any]] = []
    for item in orch:
        row = item["row"]
        cands = list(item.get("candidates") or [])
        if not cands:
            cands = merge_mock_if_empty(row, cands)
        merged.append({"row": row, "candidates": cands})
    return merged


def _specialists_parallel(merged: list[dict], deadline_days: int) -> list[dict]:
    parts: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {
            pool.submit(specialist_agent, m["row"], m["candidates"], deadline_days): m["row"]["id"]
            for m in merged
        }
        by_id: dict[int, dict] = {}
        for fut in as_completed(futs):
            by_id[int(futs[fut])] = fut.result()
        for m in merged:
            parts.append(by_id[int(m["row"]["id"])])
    return parts


def _build_summary(parts: list[dict], deadline_days: int) -> dict[str, Any]:
    total_cost = 0.0
    parts_found = 0
    parts_missing = 0
    meeting = 0
    missing_dl = 0
    for p in parts:
        if p.get("matched_mpn") and p.get("buy_url"):
            parts_found += 1
            total_cost += float(p.get("total_price") or 0)
        else:
            parts_missing += 1
        if p.get("meets_deadline"):
            meeting += 1
        else:
            missing_dl += 1
    return {
        "total_parts": len(parts),
        "total_cost_usd": round(total_cost, 2),
        "parts_found": parts_found,
        "parts_missing": parts_missing,
        "parts_meeting_deadline": meeting,
        "parts_missing_deadline": missing_dl,
        "deadline_days": deadline_days,
    }


def enrich_bom(filepath: str, deadline_days: int) -> dict[str, Any]:
    rows = parse_bom_csv(filepath)
    orch = orchestrator_agent(rows, deadline_days)
    merged = _apply_mock_fallback(orch)
    parts = _specialists_parallel(merged, deadline_days)
    return {"parts": parts, "summary": _build_summary(parts, deadline_days)}


def enrich_bom_rows(rows: list[dict], deadline_days: int) -> dict[str, Any]:
    """Same as enrich_bom but from in-memory rows (used by the built-in CLI test)."""
    orch = orchestrator_agent(rows, deadline_days)
    merged = _apply_mock_fallback(orch)
    parts = _specialists_parallel(merged, deadline_days)
    return {"parts": parts, "summary": _build_summary(parts, deadline_days)}
