"""
Orchestrator and specialist agents (CLōD / OpenAI-compatible API).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI

from .digikey_search import (
    DigiKeyConfigurationError,
    digikey_keyword_search,
    digikey_partnumber_search,
)
from .mock_search import mock_keyword_search, mock_partnumber_search

DEFAULT_CLOD_BASE_URL = "https://api.clod.io/v1"
ORCHESTRATOR_MODEL = "claude-sonnet-4-20250514"
SPECIALIST_MODEL = "claude-sonnet-4-20250514"

ORCHESTRATOR_SYSTEM = """You are an electronics component sourcing agent. You will be given BOM rows one at a time. For each row, your job is to gather the best possible list of candidate parts from DigiKey by choosing smart search strategies.

Search strategy guidelines:
- If a clear MPN exists: run digikey_partnumber_search with the MPN first, then also run digikey_keyword_search with the MPN as query to get alternatives
- If a Supplier Part number exists (e.g. LCSC C-number): run digikey_keyword_search with it, and also try the component name + footprint
- If only name + footprint (generic passive): construct a precise query like "10nF 0805 MLCC X7R" or "10kΩ 0805 1% resistor" — be specific to get relevant results. Run 1-2 keyword searches.
- You may run up to 3 searches per part to maximize candidate quality
- Once you have gathered candidates, call submit_candidates to move on

For each row you process, log:
  [ORCHESTRATOR] Row {id} ({name}): strategy = {what you decided to do}
  [ORCHESTRATOR] Row {id} ({name}): {n} candidates collected
"""

SPECIALIST_SYSTEM = """You are a specialist electronics component matching agent. You will receive:
- A single BOM row describing what part is needed
- A list of candidate parts found on DigiKey
- The project deadline in days (how long the user has to receive all parts)

Your job is to select the best candidate considering ALL of these factors:
1. Technical match — does the part actually match what's specified? (value, footprint, voltage rating, package, tolerance)
2. Availability — is it in stock? If lead_time_weeks * 7 > deadline_days, this part CANNOT arrive in time — heavily penalize or eliminate it
3. Price — lower unit price is better, but not at the cost of a wrong part
4. Stock quantity — make sure stock >= quantity needed

Deadline logic you must apply:
- Convert lead_time_weeks to days: lead_days = lead_time_weeks * 7
- Add 3 days for shipping: total_days = lead_days + 3
- If total_days > deadline_days: mark this candidate as CANNOT_MEET_DEADLINE
- Among candidates that CAN meet the deadline, pick the best technical + price match
- If NO candidate can meet the deadline, pick the closest one and flag it with a warning

Respond ONLY with a JSON object (no markdown, no explanation outside the JSON):
{
  "selected_index": <int, index into candidates array>,
  "matched_mpn": <str>,
  "matched_description": <str>,
  "unit_price": <float>,
  "total_price": <float>,
  "stock": <int>,
  "lead_time_weeks": <float>,
  "estimated_arrival_days": <int>,
  "meets_deadline": <bool>,
  "deadline_warning": <str or null>,
  "supplier_name": "DigiKey",
  "buy_url": <str>,
  "match_confidence": "high" | "medium" | "low",
  "match_reason": <str, 1-2 sentences explaining the choice>
}
"""


def _clod_base_url() -> str:
    # Match .env naming: CLOD_API_ENDPOINT (OpenAI-compatible base URL)
    base = (
        os.getenv("CLOD_API_ENDPOINT")
        or os.getenv("CLOD_BASE_URL")
        or DEFAULT_CLOD_BASE_URL
    )
    return base.rstrip("/")


def _clod_client() -> OpenAI:
    key = os.getenv("CLOD_API_KEY")
    if not key:
        raise RuntimeError(
            "CLOD_API_KEY is not set. Export it or add it to a loaded .env file "
            "(see bom_supplier_connector/env.py)."
        )
    return OpenAI(base_url=_clod_base_url(), api_key=key)


def _dedupe_candidates(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for c in items:
        key = (c.get("digikey_part_number") or "") + "|" + (c.get("mpn") or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _digikey_ready() -> bool:
    return bool(os.getenv("DIGIKEY_CLIENT_ID") and os.getenv("DIGIKEY_CLIENT_SECRET"))


def _tool_specs() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "digikey_keyword_search",
                "description": "Search DigiKey catalog by keyword string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "quantity": {"type": "integer"},
                    },
                    "required": ["query", "quantity"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "digikey_partnumber_search",
                "description": "Exact product lookup by manufacturer part number or DigiKey part number.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "part_number": {"type": "string"},
                        "quantity": {"type": "integer"},
                    },
                    "required": ["part_number", "quantity"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "submit_candidates",
                "description": "Submit all gathered candidates for this BOM row and finish.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "row_id": {"type": "integer"},
                        "candidates": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "search_summary": {"type": "string"},
                    },
                    "required": ["row_id", "candidates", "search_summary"],
                },
            },
        },
    ]


def _dispatch_tool(
    name: str,
    arguments: dict,
    row: dict,
    acc_candidates: list[dict],
    use_real_digikey: bool,
) -> tuple[str, list[dict]]:
    """Returns (message_for_model, updated_acc_candidates)."""
    if name == "digikey_keyword_search":
        q = arguments.get("query", "")
        qty = int(arguments.get("quantity", row.get("quantity") or 1))
        try:
            if use_real_digikey:
                found = digikey_keyword_search(q, qty)
            else:
                found = mock_keyword_search(q, qty)
        except DigiKeyConfigurationError:
            found = mock_keyword_search(q, qty)
        acc_candidates.extend(found)
        acc_candidates[:] = _dedupe_candidates(acc_candidates)
        return json.dumps({"count": len(found), "note": "merged into session buffer"}), acc_candidates

    if name == "digikey_partnumber_search":
        pn = arguments.get("part_number", "")
        qty = int(arguments.get("quantity", row.get("quantity") or 1))
        try:
            if use_real_digikey:
                found = digikey_partnumber_search(pn, qty)
            else:
                found = mock_partnumber_search(pn, qty)
        except DigiKeyConfigurationError:
            found = mock_partnumber_search(pn, qty)
        acc_candidates.extend(found)
        acc_candidates[:] = _dedupe_candidates(acc_candidates)
        return json.dumps({"count": len(found), "note": "merged into session buffer"}), acc_candidates

    if name == "submit_candidates":
        rid = int(row["id"])
        cand = arguments.get("candidates") or []
        summary = arguments.get("search_summary", "")
        if isinstance(cand, list) and len(cand) > 0:
            acc_candidates.clear()
            acc_candidates.extend(cand)
        acc_candidates[:] = _dedupe_candidates(acc_candidates)
        return json.dumps({"status": "ok", "row_id": rid, "submitted": len(acc_candidates), "summary": summary}), acc_candidates

    return json.dumps({"error": "unknown tool"}), acc_candidates


def orchestrator_agent(bom_rows: list[dict], deadline_days: int) -> list[dict]:
    """
    Stage 1: for each row, run tool loop with CLōD until submit_candidates or max rounds.
    """
    use_real = _digikey_ready()
    client = _clod_client()
    tools = _tool_specs()
    results: list[dict] = []

    for row in bom_rows:
        rid = int(row["id"])
        name = row.get("name") or ""
        acc: list[dict] = []
        submitted_summary = ""
        submitted = False
        messages: list[dict] = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Process this single BOM row (deadline context for planning: {deadline_days} days).\n"
                    f"Row JSON:\n{json.dumps(row, indent=2)}\n\n"
                    "Use the tools, then call submit_candidates with row_id matching this row's id "
                    "and the full deduplicated candidate list you collected."
                ),
            },
        ]

        for iteration in range(4):
            resp = client.chat.completions.create(
                model=ORCHESTRATOR_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            msg = resp.choices[0].message
            entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(entry)

            if not msg.tool_calls:
                break

            for tc in msg.tool_calls:
                fname = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if fname == "submit_candidates":
                    _msg, acc = _dispatch_tool(fname, args, row, acc, use_real)
                    submitted_summary = args.get("search_summary", "")
                    submitted = True
                    tool_content = _msg
                else:
                    tool_content, acc = _dispatch_tool(fname, args, row, acc, use_real)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_content,
                    }
                )

            if submitted:
                break

        strategy = (
            submitted_summary.strip()
            if submitted_summary
            else (
                "completed tool searches (no submit_candidates summary text)"
                if submitted
                else "stopped after max 4 iterations without submit_candidates"
            )
        )
        n = len(acc)
        print(f"[ORCHESTRATOR] Row {rid} ({name}): strategy = {strategy}")
        print(f"[ORCHESTRATOR] Row {rid} ({name}): {n} candidates collected")
        results.append(
            {
                "row": row,
                "candidates": acc,
                "orchestrator_search_summary": submitted_summary,
            }
        )

    return results


def _parse_json_object(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        text = m.group(0)
    return json.loads(text)


def specialist_agent(row: dict, candidates: list[dict], deadline_days: int) -> dict:
    """Stage 2: pick best candidate; merge decision fields into the BOM row."""
    rid = int(row["id"])
    name = row.get("name") or ""

    if not candidates:
        merged = dict(row)
        merged.update(
            {
                "selected_index": -1,
                "matched_mpn": "",
                "matched_description": "",
                "unit_price": 0.0,
                "total_price": 0.0,
                "stock": 0,
                "lead_time_weeks": 0.0,
                "estimated_arrival_days": 0,
                "meets_deadline": False,
                "deadline_warning": "No candidates from orchestrator or mock catalog.",
                "supplier_name": "DigiKey",
                "buy_url": "",
                "match_confidence": "low",
                "match_reason": "No parts to evaluate.",
            }
        )
        print(
            f"[SPECIALIST] Row {rid} ({name}): selected (none) @ $0.0 | meets deadline: False | confidence: low"
        )
        print(
            f"[SPECIALIST] Row {rid} ({name}): deadline assessment: no candidates vs {deadline_days}d project window"
        )
        return merged

    numbered = [{"index": i, **c} for i, c in enumerate(candidates)]
    user = f"""BOM Row:
  Name: {row.get("name")}
  Footprint: {row.get("footprint")}
  Quantity needed: {row.get("quantity")}
  MPN: {row.get("mpn") or "not provided"}
  Manufacturer: {row.get("manufacturer") or "not provided"}
  Supplier Part: {row.get("supplier_part") or "not provided"}

Project deadline: {deadline_days} days from today.
Parts must arrive within {deadline_days} days (include ~3 days shipping).

Candidates from DigiKey:
{json.dumps(numbered, indent=2)}
"""

    client = _clod_client()
    resp = client.chat.completions.create(
        model=SPECIALIST_MODEL,
        messages=[
            {"role": "system", "content": SPECIALIST_SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        decision = _parse_json_object(raw)
    except json.JSONDecodeError:
        decision = {
            "selected_index": 0,
            "matched_mpn": candidates[0].get("mpn", ""),
            "matched_description": candidates[0].get("description", ""),
            "unit_price": float(candidates[0].get("unit_price") or 0),
            "total_price": float(candidates[0].get("unit_price") or 0)
            * int(row.get("quantity") or 1),
            "stock": int(candidates[0].get("stock") or 0),
            "lead_time_weeks": float(candidates[0].get("lead_time_weeks") or 0),
            "estimated_arrival_days": int(float(candidates[0].get("lead_time_weeks") or 0) * 7 + 3),
            "meets_deadline": True,
            "deadline_warning": "Model returned non-JSON; defaulted to first candidate.",
            "supplier_name": "DigiKey",
            "buy_url": candidates[0].get("product_url", ""),
            "match_confidence": "low",
            "match_reason": "JSON parse failed; conservative fallback to index 0.",
        }

    idx = int(decision.get("selected_index", 0))
    if idx < 0 or idx >= len(candidates):
        idx = 0
        decision["deadline_warning"] = (decision.get("deadline_warning") or "") + " Index clamped to 0."

    pick = candidates[idx]
    qty = int(row.get("quantity") or 1)
    unit = float(decision.get("unit_price", pick.get("unit_price") or 0))
    merged = dict(row)
    merged.update(
        {
            "selected_index": idx,
            "matched_mpn": decision.get("matched_mpn") or pick.get("mpn", ""),
            "matched_description": decision.get("matched_description")
            or pick.get("description", ""),
            "unit_price": unit,
            "total_price": float(decision.get("total_price", unit * qty)),
            "stock": int(decision.get("stock", pick.get("stock") or 0)),
            "lead_time_weeks": float(
                decision.get("lead_time_weeks", pick.get("lead_time_weeks") or 0)
            ),
            "estimated_arrival_days": int(
                decision.get(
                    "estimated_arrival_days",
                    int(float(pick.get("lead_time_weeks") or 0) * 7 + 3),
                )
            ),
            "meets_deadline": bool(decision.get("meets_deadline", False)),
            "deadline_warning": decision.get("deadline_warning"),
            "supplier_name": decision.get("supplier_name", "DigiKey"),
            "buy_url": decision.get("buy_url") or pick.get("product_url", ""),
            "match_confidence": decision.get("match_confidence", "medium"),
            "match_reason": decision.get("match_reason", ""),
        }
    )

    print(
        f"[SPECIALIST] Row {rid} ({name}): selected {merged.get('matched_mpn')} @ ${merged.get('unit_price')} "
        f"| meets deadline: {merged.get('meets_deadline')} | confidence: {merged.get('match_confidence')}"
    )
    ld = int(float(merged.get("lead_time_weeks") or 0) * 7)
    tot = ld + 3
    print(
        f"[SPECIALIST] Row {rid} ({name}): deadline assessment: ~{tot} days to arrival "
        f"(lead {ld}d + 3d ship) vs {deadline_days}d project window"
    )
    return merged
