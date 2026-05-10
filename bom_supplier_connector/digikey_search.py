"""
Raw DigiKey API helpers (no agent logic).

Uses Product Information **v4** (`/products/v4/...`) via the fork in requirements.txt
(PyPI `digikey-api` 1.1.0 still targets legacy Search v3).

OAuth (from digikey-api): redirect URI is fixed to
  https://localhost:8139/digikey_callback
Register that exact URL on your DigiKey app. Use DIGIKEY_CLIENT_SANDBOX=False with
Production credentials; use True only with a Sandbox app + sandbox keys.
"""
from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from typing import Any, Optional

from .env import load_connector_env

load_connector_env()

PACKAGE_DIR = Path(__file__).resolve().parent


class DigiKeyConfigurationError(RuntimeError):
    """Raised when DigiKey client credentials are not configured."""


def _require_digikey_credentials() -> None:
    cid = os.getenv("DIGIKEY_CLIENT_ID")
    csec = os.getenv("DIGIKEY_CLIENT_SECRET")
    missing = []
    if not cid:
        missing.append("DIGIKEY_CLIENT_ID")
    if not csec:
        missing.append("DIGIKEY_CLIENT_SECRET")
    if missing:
        raise DigiKeyConfigurationError(
            "DigiKey API credentials are not set. Export: "
            + ", ".join(missing)
            + " (and optionally DIGIKEY_STORAGE_PATH, DIGIKEY_CLIENT_SANDBOX)."
        )


def _ensure_digikey_env_defaults() -> None:
    if not os.getenv("DIGIKEY_STORAGE_PATH"):
        os.environ["DIGIKEY_STORAGE_PATH"] = str(PACKAGE_DIR / "cache")
    if os.getenv("DIGIKEY_CLIENT_SANDBOX") is None:
        os.environ["DIGIKEY_CLIENT_SANDBOX"] = "False"


def _pidvid_value(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    v = getattr(obj, "value", None)
    return v if v else None


def _v4_manufacturer_name(mfr: Any) -> str:
    if mfr is None:
        return ""
    name = getattr(mfr, "name", None)
    if name:
        return str(name)
    return _pidvid_value(mfr) or ""


def _parse_lead_weeks(raw: Any) -> float:
    if raw is None:
        return 0.0
    s = str(raw).strip()
    if not s:
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1))
    return 0.0


def _unit_price_for_quantity(obj: Any, quantity: int) -> float:
    unit = getattr(obj, "unit_price", None)
    if unit is not None:
        return float(unit)
    breaks = getattr(obj, "standard_pricing", None) or []
    if not breaks:
        return 0.0
    best = None
    for pb in breaks:
        bq = getattr(pb, "break_quantity", 0) or 0
        up = getattr(pb, "unit_price", None)
        if up is None:
            continue
        if bq <= quantity and (best is None or bq >= best[0]):
            best = (bq, float(up))
    if best:
        return best[1]
    first = breaks[0]
    return float(getattr(first, "unit_price", 0.0) or 0.0)


def _v4_product_root(obj: Any) -> Any:
    """V4 `product_details` returns `ProductDetails` with a nested `product`."""
    inner = getattr(obj, "product", None)
    return inner if inner is not None else obj


def _v4_product_to_candidate(obj: Any, quantity: int) -> dict:
    root = _v4_product_root(obj)
    variations = list(getattr(root, "product_variations", None) or [])
    var0 = variations[0] if variations else None

    mpn = getattr(root, "manufacturer_product_number", None) or ""
    desc = getattr(root, "description", None) or ""
    lead_raw = getattr(root, "manufacturer_lead_weeks", None)
    mfr = _v4_manufacturer_name(getattr(root, "manufacturer", None))

    if var0:
        dkpn = getattr(var0, "digi_key_product_number", None) or ""
        stock = int(getattr(var0, "quantity_availablefor_package_type", 0) or 0)
        if stock == 0:
            stock = int(getattr(root, "quantity_available", 0) or 0)
        unit_price = float(_unit_price_for_quantity(var0, quantity))
        if unit_price == 0.0:
            up = getattr(root, "unit_price", None)
            unit_price = float(up) if up is not None else 0.0
    else:
        dkpn = ""
        stock = int(getattr(root, "quantity_available", 0) or 0)
        up = getattr(root, "unit_price", None)
        unit_price = float(up) if up is not None else 0.0
        if unit_price == 0.0:
            unit_price = float(_unit_price_for_quantity(root, quantity))

    return {
        "mpn": mpn,
        "description": desc,
        "unit_price": unit_price,
        "stock": stock,
        "lead_time_weeks": _parse_lead_weeks(lead_raw),
        "digikey_part_number": dkpn,
        "product_url": getattr(root, "product_url", None) or "",
        "manufacturer": mfr,
    }


def _import_digikey_v4():
    try:
        import digikey  # noqa: F401 — fork wires v4 into top-level API
        from digikey.v4.productinformation import KeywordRequest
    except ImportError as e:
        raise DigiKeyConfigurationError(
            "DigiKey v4 client is not available. Install the v4-capable fork from "
            "requirements.txt (see comment there), e.g.\n"
            "  pip install 'digikey-api @ git+https://github.com/hurricaneJoef/digikey-api.git'\n"
            f"ImportError: {e}"
        ) from e
    return digikey, KeywordRequest


def digikey_keyword_search(query: str, quantity: int) -> list[dict]:
    """
    Keyword search via DigiKey Product Information v4.
    """
    _ensure_digikey_env_defaults()
    _require_digikey_credentials()
    digikey, KeywordRequest = _import_digikey_v4()

    try:
        req = KeywordRequest(keywords=query, limit=8)
        result = digikey.keyword_search(body=req)
    except Exception as e:
        warnings.warn(f"[DigiKey] keyword_search failed for {query!r}: {e}")
        print(f"WARNING: DigiKey keyword_search failed for {query!r}: {e}")
        return []

    if result is None:
        print(f"WARNING: DigiKey keyword_search returned no result for {query!r}")
        return []

    products = list(getattr(result, "exact_matches", None) or [])
    products.extend(list(getattr(result, "products", None) or []))

    out: list[dict] = []
    seen: set[str] = set()
    for p in products:
        c = _v4_product_to_candidate(p, quantity)
        dk = c["digikey_part_number"]
        key = dk or (c["mpn"] + "|" + c["manufacturer"])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def digikey_partnumber_search(part_number: str, quantity: int) -> list[dict]:
    """
    Exact lookup using DigiKey or manufacturer part number (v4 `product_details`).
    """
    _ensure_digikey_env_defaults()
    _require_digikey_credentials()
    digikey, _ = _import_digikey_v4()

    try:
        details = digikey.product_details(part_number)
    except Exception as e:
        warnings.warn(f"[DigiKey] product_details failed for {part_number!r}: {e}")
        print(f"WARNING: DigiKey product_details failed for {part_number!r}: {e}")
        return []

    if details is None:
        print(f"WARNING: DigiKey product_details returned no result for {part_number!r}")
        return []

    return [_v4_product_to_candidate(details, quantity)]
