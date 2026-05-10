"""
DigiKey MyLists API client.

Spec: https://developer.digikey.com/products/mylists  (basePath /mylists/v1)

CreateList:           POST /lists                     body: CreateListRequest
AddPartsToListId:     POST /lists/{listId}/parts      body: RequestedPart[]
GetListByListId:      GET  /lists/{listId}

All endpoints require 3-legged OAuth — i.e. a token minted from the end user's
DigiKey login. The user-facing list URL (what we return so they can open it
in their browser) is `https://www.digikey.com/en/mylists/list/{listId}`.
"""
from __future__ import annotations

import os
from typing import Iterable, Optional

import requests

from .digikey_oauth import DigiKeyOAuthError

API_BASE = "https://api.digikey.com/mylists/v1"
LIST_VIEW_URL = "https://www.digikey.com/en/mylists/list/{list_id}"
TIMEOUT = 20


class DigiKeyListError(RuntimeError):
    """Raised when a MyLists API call fails."""


def _headers(access_token: str) -> dict:
    cid = os.getenv("DIGIKEY_CLIENT_ID")
    if not cid:
        raise DigiKeyOAuthError("DIGIKEY_CLIENT_ID is not set in env.")
    return {
        "Authorization": f"Bearer {access_token}",
        "X-DIGIKEY-Client-Id": cid,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_list(access_token: str, list_name: str) -> str:
    """Create an empty list in the user's DigiKey account.
    Returns the new list's id (a string).

    The CreateList endpoint's 200 response is just a JSON-encoded string id.
    """
    body = {
        "ListName": list_name,
        "Source": "external",
        "CreatedBy": "BOMA",
    }
    resp = requests.post(
        f"{API_BASE}/lists",
        headers=_headers(access_token),
        json=body,
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise DigiKeyListError(
            f"CreateList failed ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    list_id = data if isinstance(data, str) else (data.get("Id") or data.get("id") or "")
    if not list_id:
        raise DigiKeyListError(f"CreateList returned no list id: {data!r}")
    return str(list_id)


def add_parts(
    access_token: str,
    list_id: str,
    parts: Iterable[dict],
) -> list[str]:
    """Add parts to an existing list.

    Each `parts` item is a dict like
        {"part_number": "MOCK-10NF-0805-ND", "quantity": 5,
         "designator": "C1", "notes": "10nF X7R 0805"}

    Returns the list of UniqueIds DigiKey assigned to the new line items.
    """
    body = []
    for p in parts:
        pn = (p.get("part_number") or "").strip()
        qty = int(p.get("quantity") or 1)
        if not pn:
            continue
        body.append(
            {
                "RequestedPartNumber": pn,
                "ReferenceDesignator": p.get("designator") or "",
                "Notes": p.get("notes") or "",
                "Quantities": [{"Quantity": qty}],
            }
        )
    if not body:
        return []

    resp = requests.post(
        f"{API_BASE}/lists/{list_id}/parts",
        headers=_headers(access_token),
        json=body,
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise DigiKeyListError(
            f"AddPartsToListId failed ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    if isinstance(data, list):
        return [str(x) for x in data]
    return []


def list_view_url(list_id: str) -> str:
    return LIST_VIEW_URL.format(list_id=list_id)


def create_list_with_parts(
    access_token: str,
    list_name: str,
    parts: list[dict],
) -> dict:
    """Convenience: CreateList + AddPartsToListId in one call. Returns
    {list_id, list_url, added_unique_ids}. Skips parts with no DigiKey
    part number rather than failing the whole batch."""
    list_id = create_list(access_token, list_name)
    valid = [p for p in parts if (p.get("part_number") or "").strip()]
    skipped = [p for p in parts if not (p.get("part_number") or "").strip()]
    unique_ids: list[str] = []
    if valid:
        unique_ids = add_parts(access_token, list_id, valid)
    return {
        "list_id": list_id,
        "list_url": list_view_url(list_id),
        "added_unique_ids": unique_ids,
        "added_count": len(valid),
        "skipped_count": len(skipped),
    }
