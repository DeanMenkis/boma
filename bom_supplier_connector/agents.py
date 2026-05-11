"""
Orchestrator and specialist agents (CLōD / OpenAI-compatible API).
"""
from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

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


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


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
- The project deadline in days (how long the user has to receive all parts).
  May be the literal string "none" — meaning the user did not give a deadline.

Your job is to select the best candidate considering ALL of these factors:
1. Technical match — does the part actually match what's specified? (value, footprint, voltage rating, package, tolerance)
2. Availability — is it in stock? If a deadline was given and lead_time_weeks * 7 + 3 > deadline_days, this part CANNOT arrive in time — heavily penalize or eliminate it
3. Price — lower unit price is better, but not at the cost of a wrong part
4. Stock quantity — make sure stock >= quantity needed

Deadline logic you must apply:
- If deadline is "none": skip the deadline filter entirely. Among technically-matching, in-stock candidates pick the cheapest. Set "meets_deadline": true.
- Otherwise: convert lead_time_weeks to days (lead_days = lead_time_weeks * 7), add 3 days shipping (total_days = lead_days + 3).
  - If total_days > deadline_days: this candidate CANNOT_MEET_DEADLINE.
  - Among candidates that CAN meet the deadline, prefer the cheapest *that arrives soonest*.
  - If NO candidate can meet the deadline, pick the soonest-arriving one and flag deadline_warning.

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
    """True only when we should try the real DigiKey API.

    Set ``BOMA_USE_MOCK_CATALOG=1`` (or ``BOMA_DIGIKEY_DISABLE=1``) to force
    the orchestrator into mock mode even when ``DIGIKEY_CLIENT_ID/SECRET``
    are present. Useful when the OAuth token cache is empty in a non-
    interactive process (uvicorn) and triggering the browser flow would
    hang the request.
    """
    if os.getenv("BOMA_USE_MOCK_CATALOG") or os.getenv("BOMA_DIGIKEY_DISABLE"):
        return False
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
    rid = int(row.get("id") or 0)
    if name == "digikey_keyword_search":
        q = arguments.get("query", "")
        qty = int(arguments.get("quantity", row.get("quantity") or 1))
        _log(
            f"[ORCH row={rid}] tool=digikey_keyword_search qty={qty} query={q!r} "
            f"(real_digikey={use_real_digikey}) …"
        )
        t0 = time.perf_counter()
        try:
            if use_real_digikey:
                found = digikey_keyword_search(q, qty)
            else:
                found = mock_keyword_search(q, qty)
        except DigiKeyConfigurationError:
            found = mock_keyword_search(q, qty)
        acc_candidates.extend(found)
        acc_candidates[:] = _dedupe_candidates(acc_candidates)
        dt = time.perf_counter() - t0
        _log(
            f"[ORCH row={rid}] digikey_keyword_search done in {dt:.2f}s "
            f"hits={len(found)} buffer={len(acc_candidates)}"
        )
        return json.dumps({"count": len(found), "note": "merged into session buffer"}), acc_candidates

    if name == "digikey_partnumber_search":
        pn = arguments.get("part_number", "")
        qty = int(arguments.get("quantity", row.get("quantity") or 1))
        _log(
            f"[ORCH row={rid}] tool=digikey_partnumber_search qty={qty} pn={pn!r} "
            f"(real_digikey={use_real_digikey}) …"
        )
        t0 = time.perf_counter()
        try:
            if use_real_digikey:
                found = digikey_partnumber_search(pn, qty)
            else:
                found = mock_partnumber_search(pn, qty)
        except DigiKeyConfigurationError:
            found = mock_partnumber_search(pn, qty)
        acc_candidates.extend(found)
        acc_candidates[:] = _dedupe_candidates(acc_candidates)
        dt = time.perf_counter() - t0
        _log(
            f"[ORCH row={rid}] digikey_partnumber_search done in {dt:.2f}s "
            f"hits={len(found)} buffer={len(acc_candidates)}"
        )
        return json.dumps({"count": len(found), "note": "merged into session buffer"}), acc_candidates

    if name == "submit_candidates":
        rid_submit = int(row["id"])
        cand = arguments.get("candidates") or []
        summary = arguments.get("search_summary", "")
        if isinstance(cand, list) and len(cand) > 0:
            acc_candidates.clear()
            acc_candidates.extend(cand)
        acc_candidates[:] = _dedupe_candidates(acc_candidates)
        _log(
            f"[ORCH row={rid_submit}] tool=submit_candidates payload_lines="
            f"{len(cand) if isinstance(cand, list) else 0} buffer={len(acc_candidates)}"
        )
        return (
            json.dumps(
                {
                    "status": "ok",
                    "row_id": rid_submit,
                    "submitted": len(acc_candidates),
                    "summary": summary,
                }
            ),
            acc_candidates,
        )

    return json.dumps({"error": "unknown tool"}), acc_candidates


def _orchestrate_row(row: dict, deadline_days: Optional[int], use_real: bool) -> dict:
    """Run the orchestrator tool loop for a single BOM row.
    Returns {"row": row, "candidates": [...], "orchestrator_search_summary": str}.

    Pure per-row work so this function is safe to run concurrently from a
    ThreadPoolExecutor (each call gets its own OpenAI client + message list).
    """
    rid = int(row["id"])
    name = row.get("name") or ""
    _log(
        f"[ORCH row={rid}] start orchestrator name={name!r} "
        f"use_real_digikey={use_real} deadline_days={deadline_days!r}"
    )
    client = _clod_client()
    tools = _tool_specs()
    acc: list[dict] = []
    submitted_summary = ""
    submitted = False

    deadline_text = (
        f"deadline context for planning: {deadline_days} days"
        if deadline_days is not None
        else "no project deadline supplied — optimize for cheapest in-stock part"
    )

    messages: list[dict] = [
        {"role": "system", "content": ORCHESTRATOR_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Process this single BOM row ({deadline_text}).\n"
                f"Row JSON:\n{json.dumps(row, indent=2)}\n\n"
                "Use the tools, then call submit_candidates with row_id matching this row's id "
                "and the full deduplicated candidate list you collected."
            ),
        },
    ]

    for iter_idx in range(4):
        _log(
            f"[ORCH row={rid}] CLōD orchestrator chat.completions "
            f"iteration {iter_idx + 1}/4 (model={ORCHESTRATOR_MODEL}) …"
        )
        t_llm = time.perf_counter()
        resp = client.chat.completions.create(
            model=ORCHESTRATOR_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        llm_dt = time.perf_counter() - t_llm
        msg = resp.choices[0].message
        n_tools = len(msg.tool_calls or [])
        _log(
            f"[ORCH row={rid}] CLōD returned in {llm_dt:.2f}s "
            f"tool_calls={n_tools} content_len={len((msg.content or ''))}"
        )
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
            _log(f"[ORCH row={rid}] model returned no tool_calls — ending orchestrator loop")
            break

        for tc in msg.tool_calls:
            fname = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            _log(f"[ORCH row={rid}] executing tool {fname!r} …")
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
    print(f"[ORCHESTRATOR] Row {rid} ({name}): strategy = {strategy}", flush=True)
    print(f"[ORCHESTRATOR] Row {rid} ({name}): {len(acc)} candidates collected", flush=True)
    _log(f"[ORCH row={rid}] orchestrator finished")

    return {
        "row": row,
        "candidates": acc,
        "orchestrator_search_summary": submitted_summary,
    }


# Cap concurrency so we don't hammer CLōD or DigiKey rate limits even when
# someone uploads a 100-row BOM.
_ORCHESTRATOR_MAX_WORKERS = int(os.getenv("BOMA_ORCHESTRATOR_MAX_WORKERS", "10"))


def orchestrator_agent(
    bom_rows: list[dict], deadline_days: Optional[int]
) -> list[dict]:
    """Stage 1: spin up one orchestrator agent per BOM row in parallel.

    Each row gets its own CLōD tool loop. Results are reordered to match the
    original row order so downstream stages stay deterministic.
    """
    use_real = _digikey_ready()
    if not bom_rows:
        return []

    workers = min(len(bom_rows), max(1, _ORCHESTRATOR_MAX_WORKERS))
    print(
        f"[ORCHESTRATOR] dispatching {len(bom_rows)} rows across {workers} parallel workers",
        flush=True,
    )
    if use_real and workers > 1:
        _log(
            "[ORCHESTRATOR] note: real DigiKey + parallel orchestrators can race on "
            "OAuth token refresh; digikey-api may open a localhost browser window and "
            "appear to hang. Set BOMA_ORCHESTRATOR_MAX_WORKERS=1 to run one row at a time."
        )

    results_by_id: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_orchestrate_row, row, deadline_days, use_real): int(row["id"])
            for row in bom_rows
        }
        _log("[ORCHESTRATOR] all row tasks submitted; waiting for workers (order may vary)…")
        for fut in as_completed(futures):
            rid = futures[fut]
            _log(f"[ORCHESTRATOR] worker completing row_id={rid} (fetching result)…")
            try:
                results_by_id[rid] = fut.result()
                nc = len(results_by_id[rid].get("candidates") or [])
                _log(f"[ORCHESTRATOR] row_id={rid} done candidates={nc}")
            except Exception as e:
                # Don't let one bad row kill the whole sourcing run.
                print(f"[ORCHESTRATOR] Row {rid}: ERROR — {e}", flush=True)
                # Re-find the row so the specialist still gets to run with no candidates.
                row = next(r for r in bom_rows if int(r["id"]) == rid)
                results_by_id[rid] = {
                    "row": row,
                    "candidates": [],
                    "orchestrator_search_summary": f"orchestrator crashed: {e}",
                }

    _log("[ORCHESTRATOR] all row workers finished; returning ordered results")
    return [results_by_id[int(r["id"])] for r in bom_rows]


def _parse_json_object(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        text = m.group(0)
    return json.loads(text)


def specialist_agent(
    row: dict, candidates: list[dict], deadline_days: Optional[int]
) -> dict:
    """Stage 2: pick best candidate; merge decision fields into the BOM row.

    `deadline_days=None` means the user didn't give a deadline — pick the
    cheapest in-stock part and treat meets_deadline as True.
    """
    rid = int(row["id"])
    name = row.get("name") or ""
    no_deadline = deadline_days is None

    if not candidates:
        _log(f"[SPEC row={rid}] specialist skip — 0 candidates")
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
                "digikey_part_number": "",
                "match_confidence": "low",
                "match_reason": "No parts to evaluate.",
            }
        )
        deadline_label = "no deadline" if no_deadline else f"{deadline_days}d project window"
        print(
            f"[SPECIALIST] Row {rid} ({name}): selected (none) @ $0.0 | meets deadline: False | confidence: low",
            flush=True,
        )
        print(
            f"[SPECIALIST] Row {rid} ({name}): deadline assessment: no candidates vs {deadline_label}",
            flush=True,
        )
        return merged

    _log(
        f"[SPEC row={rid}] specialist start candidates={len(candidates)} "
        f"model={SPECIALIST_MODEL} deadline_days={deadline_days!r}"
    )
    numbered = [{"index": i, **c} for i, c in enumerate(candidates)]
    deadline_block = (
        f"Project deadline: {deadline_days} days from today.\n"
        f"Parts must arrive within {deadline_days} days (include ~3 days shipping)."
        if not no_deadline
        else (
            "Project deadline: none — the user did not give a deadline.\n"
            "Pick the cheapest in-stock candidate that technically matches. "
            'Set "meets_deadline": true.'
        )
    )
    user = f"""BOM Row:
  Name: {row.get("name")}
  Footprint: {row.get("footprint")}
  Quantity needed: {row.get("quantity")}
  MPN: {row.get("mpn") or "not provided"}
  Manufacturer: {row.get("manufacturer") or "not provided"}
  Supplier Part: {row.get("supplier_part") or "not provided"}

{deadline_block}

Candidates from DigiKey:
{json.dumps(numbered, indent=2, default=str)}
"""

    client = _clod_client()
    _log(f"[SPEC row={rid}] CLōD specialist chat.completions …")
    t_sp = time.perf_counter()
    resp = client.chat.completions.create(
        model=SPECIALIST_MODEL,
        messages=[
            {"role": "system", "content": SPECIALIST_SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    _log(f"[SPEC row={rid}] CLōD specialist returned in {time.perf_counter() - t_sp:.2f}s")
    raw = (resp.choices[0].message.content or "").strip()
    try:
        decision = _parse_json_object(raw)
    except json.JSONDecodeError:
        # Fallback to cheapest in-stock candidate. Compute meets_deadline
        # honestly when a deadline was given (previously hard-coded True,
        # which silently broke Step 2's availability check on parse errors).
        in_stock = [
            (i, c) for i, c in enumerate(candidates)
            if int(c.get("stock") or 0) >= int(row.get("quantity") or 1)
        ] or list(enumerate(candidates))
        idx, pick = min(
            in_stock, key=lambda ic: float(ic[1].get("unit_price") or 0) or 1e9
        )
        first_lead_weeks = float(pick.get("lead_time_weeks") or 0)
        first_arrival_days = int(first_lead_weeks * 7 + 3)
        meets = True if no_deadline else first_arrival_days <= deadline_days
        late_msg = (
            ""
            if no_deadline or meets
            else f" Estimated arrival {first_arrival_days}d exceeds deadline {deadline_days}d."
        )
        decision = {
            "selected_index": idx,
            "matched_mpn": pick.get("mpn", ""),
            "matched_description": pick.get("description", ""),
            "unit_price": float(pick.get("unit_price") or 0),
            "total_price": float(pick.get("unit_price") or 0)
            * int(row.get("quantity") or 1),
            "stock": int(pick.get("stock") or 0),
            "lead_time_weeks": first_lead_weeks,
            "estimated_arrival_days": first_arrival_days,
            "meets_deadline": meets,
            "deadline_warning": "Model returned non-JSON; defaulted to cheapest in-stock candidate." + late_msg,
            "supplier_name": "DigiKey",
            "buy_url": pick.get("product_url", ""),
            "match_confidence": "low",
            "match_reason": "JSON parse failed; conservative fallback to cheapest in-stock candidate.",
        }

    idx = int(decision.get("selected_index", 0))
    if idx < 0 or idx >= len(candidates):
        idx = 0
        decision["deadline_warning"] = (decision.get("deadline_warning") or "") + " Index clamped to 0."

    pick = candidates[idx]
    qty = int(row.get("quantity") or 1)
    # Coalesce to handle the model returning explicit JSON nulls — `dict.get`
    # only falls back to its default when the key is *missing*, not when its
    # value is None, which used to crash float()/int() conversions.
    unit = float(_coerce_num(decision.get("unit_price"), pick.get("unit_price"), 0))
    total = float(_coerce_num(decision.get("total_price"), unit * qty, 0))
    stock = int(_coerce_num(decision.get("stock"), pick.get("stock"), 0))
    lead_weeks = float(_coerce_num(decision.get("lead_time_weeks"), pick.get("lead_time_weeks"), 0))
    arrival_days = int(_coerce_num(decision.get("estimated_arrival_days"), int(lead_weeks * 7 + 3), 0))

    merged = dict(row)
    merged.update(
        {
            "selected_index": idx,
            "matched_mpn": decision.get("matched_mpn") or pick.get("mpn", ""),
            "matched_description": decision.get("matched_description")
            or pick.get("description", ""),
            "unit_price": unit,
            "total_price": total,
            "stock": stock,
            "lead_time_weeks": lead_weeks,
            "estimated_arrival_days": arrival_days,
            "meets_deadline": bool(decision.get("meets_deadline", False)),
            "deadline_warning": decision.get("deadline_warning"),
            "supplier_name": decision.get("supplier_name", "DigiKey"),
            "buy_url": decision.get("buy_url") or pick.get("product_url", ""),
            # Carry the DKPN through so we can add this part to a DigiKey list later.
            "digikey_part_number": pick.get("digikey_part_number", ""),
            "match_confidence": decision.get("match_confidence", "medium"),
            "match_reason": decision.get("match_reason", ""),
        }
    )

    print(
        f"[SPECIALIST] Row {rid} ({name}): selected {merged.get('matched_mpn')} @ ${merged.get('unit_price')} "
        f"| meets deadline: {merged.get('meets_deadline')} | confidence: {merged.get('match_confidence')}",
        flush=True,
    )
    ld = int(lead_weeks * 7)
    tot = ld + 3
    deadline_label = "no deadline" if no_deadline else f"{deadline_days}d project window"
    print(
        f"[SPECIALIST] Row {rid} ({name}): deadline assessment: ~{tot} days to arrival "
        f"(lead {ld}d + 3d ship) vs {deadline_label}",
        flush=True,
    )
    _log(f"[SPEC row={rid}] specialist finished dkpn={merged.get('digikey_part_number')!r}")
    return merged


def _coerce_num(*candidates_: Any) -> float:
    """Return the first numeric, non-None argument, else 0.
    Used to defend against the LLM returning explicit `null` for numeric
    fields, which would otherwise crash float()/int() conversions."""
    for v in candidates_:
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0
