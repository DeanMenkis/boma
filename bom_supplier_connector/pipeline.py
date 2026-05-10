"""
BOM CSV parsing and enrich_bom main pipeline.
"""
from __future__ import annotations

import csv
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

from . import digikey_lists
from .agents import orchestrator_agent, specialist_agent
from .mock_search import merge_mock_if_empty


def _plog(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] [PIPELINE] {msg}", flush=True)


def _read_csv_text(path: Path) -> str:
    """Read CSV as text; support UTF-8, UTF-8 BOM, and UTF-16 LE/BE (Excel export)."""
    peek = path.read_bytes()[:4]
    if peek.startswith(b"\xff\xfe"):
        return path.read_text(encoding="utf-16-le", errors="replace")
    if peek.startswith(b"\xfe\xff"):
        return path.read_text(encoding="utf-16-be", errors="replace")
    if peek.startswith(b"\xef\xbb\xbf"):
        return path.read_text(encoding="utf-8-sig", errors="replace")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_bom_csv(filepath: str) -> list[dict]:
    path = Path(filepath)
    text = _read_csv_text(path)
    if text.startswith("\ufeff"):
        text = text[1:]
    first = (text.splitlines()[0] if text else "").strip("\r")
    delim = (
        "\t"
        if "\t" in first and first.count("\t") > first.count(",")
        else ","
    )
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delim)
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


def _specialists_parallel(merged: list[dict], deadline_days: Optional[int]) -> list[dict]:
    parts: list[dict] = []
    workers = min(max(1, len(merged)), 10)
    _plog(f"specialist stage: {len(merged)} rows, max_workers={workers}")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(specialist_agent, m["row"], m["candidates"], deadline_days): m["row"]["id"]
            for m in merged
        }
        by_id: dict[int, dict] = {}
        for fut in as_completed(futs):
            rid = int(futs[fut])
            _plog(f"specialist worker finishing row_id={rid} …")
            by_id[rid] = fut.result()
            dk = (by_id[rid].get("digikey_part_number") or "")[:24]
            _plog(f"specialist row_id={rid} done dkpn_prefix={dk!r}")
        for m in merged:
            parts.append(by_id[int(m["row"]["id"])])
    _plog("specialist stage complete")
    return parts


def _digikey_mylist_lines(parts: list[dict]) -> list[dict]:
    """Rows for ``digikey_lists.create_list_with_parts`` (DigiKey part number + qty + notes)."""
    return [
        {
            "part_number": p.get("digikey_part_number") or "",
            "quantity": int(p.get("quantity") or 1),
            "designator": p.get("designator") or "",
            "notes": (p.get("match_reason") or "")[:500],
        }
        for p in parts
        if p.get("digikey_part_number")
    ]


def _attach_digikey_third_party_mylist(
    result: dict[str, Any],
    *,
    list_name_suffix: str,
) -> None:
    """Mutates ``result`` with ``digikey_list`` / ``list_url`` or ``digikey_list_error``."""
    lines = _digikey_mylist_lines(result.get("parts") or [])
    if not lines:
        _plog("DigiKey third-party MyList skipped (no digikey_part_number on any row)")
        return
    label = (list_name_suffix or "BOMA BOM").strip() or "BOMA BOM"
    _plog(f"DigiKey third-party MyList POST ({len(lines)} lines) list={label!r} …")
    t0 = time.perf_counter()
    try:
        info = digikey_lists.create_list_with_parts(
            list_name=f"BOMA — {label}",
            parts=lines,
        )
        result["digikey_list"] = info
        result["list_url"] = info.get("list_url") or info.get("single_use_url")
        _plog(f"DigiKey MyList OK in {time.perf_counter() - t0:.2f}s")
    except digikey_lists.DigiKeyListError as e:
        result["digikey_list_error"] = str(e)
        _plog(f"DigiKey MyList error after {time.perf_counter() - t0:.2f}s: {e}")


def _build_summary(parts: list[dict], deadline_days: Optional[int]) -> dict[str, Any]:
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


def enrich_bom(
    filepath: str,
    deadline_days: Optional[int] = None,
    digikey_list_name: Optional[str] = None,
) -> dict[str, Any]:
    rows = parse_bom_csv(filepath)
    label = (
        digikey_list_name
        if digikey_list_name is not None
        else Path(filepath).stem
    )
    return enrich_bom_rows(rows, deadline_days, digikey_list_name=label)


def enrich_bom_rows(
    rows: list[dict],
    deadline_days: Optional[int] = None,
    digikey_list_name: Optional[str] = None,
) -> dict[str, Any]:
    """Run the orchestrator (parallel per row) + specialist (parallel) on
    in-memory rows. `deadline_days=None` means "no deadline; pick cheapest".

    After enrichment, builds a DigiKey third-party MyList (single-use URL) when
    at least one row has ``digikey_part_number``. ``digikey_list_name`` sets the
    list title suffix after ``BOMA —`` (default: ``enriched BOM`` for in-memory
    runs without a file path)."""
    _plog(f"start enrich_bom_rows rows={len(rows)} deadline_days={deadline_days!r}")
    t0 = time.perf_counter()
    _plog("stage 1/4: orchestrator_agent …")
    orch = orchestrator_agent(rows, deadline_days)
    _plog(f"stage 1 done in {time.perf_counter() - t0:.2f}s")
    _plog("stage 2/4: mock fallback merge …")
    t1 = time.perf_counter()
    merged = _apply_mock_fallback(orch)
    _plog(f"stage 2 done in {time.perf_counter() - t1:.2f}s ({len(merged)} rows)")
    _plog("stage 3/4: specialist_agent (parallel) …")
    t2 = time.perf_counter()
    parts = _specialists_parallel(merged, deadline_days)
    _plog(f"stage 3 done in {time.perf_counter() - t2:.2f}s")
    result: dict[str, Any] = {
        "parts": parts,
        "summary": _build_summary(parts, deadline_days),
    }
    list_label = (digikey_list_name or "enriched BOM").strip() or "enriched BOM"
    _plog("stage 4/4: DigiKey third-party MyList …")
    _attach_digikey_third_party_mylist(result, list_name_suffix=list_label)
    _plog(f"enrich_bom_rows finished total_elapsed={time.perf_counter() - t0:.2f}s")
    return result
