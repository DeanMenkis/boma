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
import re
from typing import Any, Iterable

import requests

# Cloudflare in front of digikey.com fingerprints TLS — plain `requests`
# (urllib3) is blocked with a 403 even with a perfect browser User-Agent.
# `curl_cffi` impersonates Chrome's TLS handshake and is allowed through.
# We import it lazily so the package still loads on systems without it.
try:
    from curl_cffi import requests as _cffi_requests
except ImportError:  # pragma: no cover - optional fallback
    _cffi_requests = None  # type: ignore[assignment]

THIRD_PARTY_MYLIST_URL = "https://www.digikey.com/mylists/api/thirdparty"
TIMEOUT = 20

# Cloudflare fingerprints TLS; rotate impersonations when one starts failing.
_DEFAULT_IMPERSONATIONS = ("chrome136", "chrome124", "chrome120", "chrome110")

DEFAULT_REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _impersonate_profiles() -> tuple[str, ...]:
    raw = (os.getenv("DIGIKEY_MYLIST_IMPERSONATE") or "").strip()
    if raw:
        return tuple(p.strip() for p in raw.split(",") if p.strip())
    return _DEFAULT_IMPERSONATIONS


def _looks_like_cloudflare_block(status: int, text: str) -> bool:
    if status == 403:
        return True
    t = text.lstrip()[:800].lower()
    return "<title>just a moment" in t or "cf-mitigated" in t


def _post_mylist(url: str, params: dict, body: list[dict]) -> tuple[int, str]:
    """POST to the third-party MyLists endpoint.

    Prefers `curl_cffi` (Chrome TLS fingerprint) to defeat Cloudflare's bot
    challenge; falls back to plain `requests` (which will likely 403, but
    surfaces a useful error message if `curl_cffi` is missing).
    """
    if _cffi_requests is None:
        resp = requests.post(
            url,
            params=params,
            json=body,
            headers=DEFAULT_REQUEST_HEADERS,
            timeout=TIMEOUT,
        )
        return resp.status_code, resp.text

    last_status = 0
    last_text = ""
    for impersonate in _impersonate_profiles():
        resp = _cffi_requests.post(
            url,
            params=params,
            json=body,
            headers=DEFAULT_REQUEST_HEADERS,
            timeout=TIMEOUT,
            impersonate=impersonate,
        )
        last_status, last_text = resp.status_code, resp.text
        if resp.status_code == 200 and not _looks_like_cloudflare_block(
            resp.status_code, resp.text
        ):
            return last_status, last_text
        if not _looks_like_cloudflare_block(resp.status_code, resp.text):
            return last_status, last_text
    return last_status, last_text


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


_HTTP_URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def _extract_url_from_json_obj(obj: Any, depth: int = 0) -> str | None:
    """Best-effort find a DigiKey short/list URL in nested JSON."""
    if depth > 8:
        return None
    if isinstance(obj, str):
        s = obj.strip()
        if s.startswith("http://") or s.startswith("https://"):
            return s.split()[0]
        return None
    if isinstance(obj, dict):
        for key in (
            "singleUseUrl",
            "single_use_url",
            "SingleUseUrl",
            "url",
            "Url",
            "redirectUrl",
            "RedirectUrl",
            "link",
        ):
            v = obj.get(key)
            found = _extract_url_from_json_obj(v, depth + 1)
            if found:
                return found
        for v in obj.values():
            found = _extract_url_from_json_obj(v, depth + 1)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _extract_url_from_json_obj(item, depth + 1)
            if found:
                return found
    return None


def _parse_third_party_url(raw_text: str) -> str:
    """Normalize response: JSON string URL, plain URL, or ``{singleUseUrl: ...}``."""
    text = raw_text.strip()
    if not text:
        raise DigiKeyListError("Empty response body from third-party MyLists.")

    parsed: Any
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if text.startswith("http://") or text.startswith("https://"):
            return text.split()[0]
        m = _HTTP_URL_RE.search(text)
        if m:
            return m.group(0).rstrip('",)')
        raise DigiKeyListError(f"Unparseable response: {text[:500]}") from None

    found = _extract_url_from_json_obj(parsed)
    if found:
        return found

    raise DigiKeyListError(f"No single-use URL in response: {text[:800]}")


def merge_list_parts_by_dkpn(parts: Iterable[dict]) -> list[dict]:
    """Merge duplicate ``part_number`` rows (sum qty, join designators).

    DigiKey accepts duplicate lines, but merging avoids oversized payloads and
    matches KiCad-style BOM grouping.
    """
    by_pn: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for p in parts:
        pn = (p.get("part_number") or "").strip()
        if not pn:
            continue
        qty = max(1, int(p.get("quantity") or 1))
        des = (p.get("designator") or "").strip()
        note = (p.get("notes") or "").strip()
        if pn not in by_pn:
            by_pn[pn] = {
                "part_number": pn,
                "quantity": qty,
                "designator": des,
                "notes": note,
            }
            order.append(pn)
            continue
        acc = by_pn[pn]
        acc["quantity"] = int(acc.get("quantity") or 1) + qty
        if des:
            prev = (acc.get("designator") or "").strip()
            merged = f"{prev},{des}" if prev else des
            acc["designator"] = merged[:120]
    return [by_pn[k] for k in order]


def create_list_with_parts(list_name: str, parts: list[dict]) -> dict[str, Any]:
    """Create a third-party MyList and return the single-use URL.

    ``parts`` items may include ``part_number`` (DigiKey part number),
    ``quantity`` (default 1), and optionally ``designator`` / ``notes`` mapped
    to ``customerReference`` / ``notes`` in the payload.

    Returns ``single_use_url`` and ``list_url`` (same value), plus counts.
    """
    if _cffi_requests is None:
        raise DigiKeyListError(
            "DigiKey MyLists requires curl_cffi (Cloudflare blocks plain TLS). "
            "Install: pip install curl_cffi"
        )

    merged = merge_list_parts_by_dkpn(parts)
    body = _third_party_parts_json_array(merged)
    if not body:
        raise DigiKeyListError(
            "No parts with a non-empty part_number (DigiKey part number) to send."
        )

    tags = (os.getenv("DIGIKEY_MYLIST_TAGS") or "BOMA").strip() or "BOMA"
    params = {"listName": list_name, "tags": tags}

    status, text = _post_mylist(THIRD_PARTY_MYLIST_URL, params, body)
    if status != 200 or _looks_like_cloudflare_block(status, text):
        hint = ""
        if _looks_like_cloudflare_block(status, text):
            hint = (
                " Cloudflare blocked the server request (TLS fingerprint). "
                "Ensure curl_cffi is installed and upgrade if needed: pip install -U curl_cffi"
            )
        raise DigiKeyListError(
            f"Third-party MyLists failed ({status}): {text[:800]}{hint}"
        )

    single = _parse_third_party_url(text)

    valid = [p for p in parts if (p.get("part_number") or "").strip()]
    skipped = [p for p in parts if not (p.get("part_number") or "").strip()]

    return {
        "single_use_url": single,
        "list_url": single,
        "added_count": len(body),
        "skipped_count": len(skipped),
        "merged_unique_parts": len(body),
    }
