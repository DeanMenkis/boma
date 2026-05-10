"""
DigiKey Third-Party MyLists — unauthenticated HTTP API.

POST ``https://www.digikey.com/mylists/api/thirdparty`` with:

- **Query string:** ``listName`` (list title) and ``tags`` (DigiKey uses this
  for integration analytics; default ``BOMA``, override with
  ``DIGIKEY_MYLIST_TAGS``).
- **JSON body:** a **JSON array** of line objects (not a wrapper object), each
  with ``requestedPartNumber``, ``quantities`` (``[{"quantity": n}]``), and
  optionally ``customerReference`` / ``notes`` (DigiKey accepts empty strings).

The successful response body is typically a **JSON-encoded string** — a
one-time ``https://www.digikey.com/short/…`` URL (same pattern as Digi-Key’s
KiCad-Push-to-DigiKey plugin). Some responses may instead be a JSON object
with a ``singleUseUrl`` field; both shapes are handled.

No OAuth, API keys, or ``X-DIGIKEY-*`` headers.
"""
from __future__ import annotations

import json
import os
from typing import Any, Iterable

import requests

THIRD_PARTY_MYLIST_URL = "https://www.digikey.com/mylists/api/thirdparty"
TIMEOUT = 20

DEFAULT_REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "boma-supplier-connector/1.0",
}


class DigiKeyListError(RuntimeError):
    """Raised when the Third-Party MyLists API call fails or returns an unexpected body."""


def _third_party_parts_json_array(parts: Iterable[dict]) -> list[dict]:
    """Build the top-level JSON array DigiKey expects in the POST body."""
    out: list[dict] = []
    for p in parts:
        pn = (p.get("part_number") or "").strip()
        if not pn:
            continue
        qty = int(p.get("quantity") or 1)
        out.append(
            {
                "requestedPartNumber": pn,
                "quantities": [{"quantity": qty}],
                "customerReference": (p.get("designator") or "")[:120],
                "notes": (p.get("notes") or "")[:500],
            }
        )
    return out


def _parse_third_party_url(raw_text: str) -> str:
    """Normalize response: JSON string URL, plain URL, or ``{singleUseUrl: ...}``."""
    text = raw_text.strip()
    if not text:
        raise DigiKeyListError("Empty response body from third-party MyLists.")

    parsed: str | dict[str, Any]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if text.startswith("http://") or text.startswith("https://"):
            return text
        raise DigiKeyListError(f"Unparseable response: {text[:500]}") from None

    if isinstance(parsed, str) and parsed.startswith("http"):
        return parsed.strip()

    if isinstance(parsed, dict):
        url = (
            (parsed.get("singleUseUrl") or parsed.get("single_use_url") or "")
            .strip()
        )
        if url:
            return url

    raise DigiKeyListError(f"No single-use URL in response: {text[:800]}")


def create_list_with_parts(list_name: str, parts: list[dict]) -> dict[str, Any]:
    """Create a third-party MyList and return the single-use URL.

    ``parts`` items may include ``part_number`` (DigiKey part number),
    ``quantity`` (default 1), and optionally ``designator`` / ``notes`` mapped
    to ``customerReference`` / ``notes`` in the payload.

    Returns ``single_use_url`` and ``list_url`` (same value), plus counts.
    """
    body = _third_party_parts_json_array(parts)
    if not body:
        raise DigiKeyListError(
            "No parts with a non-empty part_number (DigiKey part number) to send."
        )

    tags = (os.getenv("DIGIKEY_MYLIST_TAGS") or "BOMA").strip() or "BOMA"
    params = {"listName": list_name, "tags": tags}

    resp = requests.post(
        THIRD_PARTY_MYLIST_URL,
        params=params,
        json=body,
        headers=DEFAULT_REQUEST_HEADERS,
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise DigiKeyListError(
            f"Third-party MyLists failed ({resp.status_code}): {resp.text[:800]}"
        )

    single = _parse_third_party_url(resp.text)

    valid = [p for p in parts if (p.get("part_number") or "").strip()]
    skipped = [p for p in parts if not (p.get("part_number") or "").strip()]

    return {
        "single_use_url": single,
        "list_url": single,
        "added_count": len(body),
        "skipped_count": len(skipped),
    }
