#!/usr/bin/env python3
"""
DigiKey OAuth + single keyword search smoke test.

Developer portal setup (must match the digikey-api library exactly):
  • Callback / redirect URL: https://localhost:8139/digikey_callback
    (NOT https://localhost — mismatches cause auth failures.)
  • Your app must include Product Information v4; this repo uses the v4 fork
    from requirements.txt (see bom_supplier_connector/digikey_search.py).

Environment (Production app — typical):
  DIGIKEY_CLIENT_ID
  DIGIKEY_CLIENT_SECRET
  DIGIKEY_CLIENT_SANDBOX=False   # required for Production client id/secret
  DIGIKEY_STORAGE_PATH           # optional; defaults to bom_supplier_connector/cache

Only set DIGIKEY_CLIENT_SANDBOX=True if you registered a Sandbox app and use
sandbox client id/secret from the portal.

After any failed OAuth or API version change, clear the token cache, then rerun:
  rm -rf bom_supplier_connector/cache/*
  export DIGIKEY_CLIENT_SANDBOX=False
  python bom_supplier_connector/test_digikey_keyword.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    from bom_supplier_connector.digikey_search import (
        DigiKeyConfigurationError,
        digikey_keyword_search,
    )

    print("DigiKey keyword search smoke test (digikey-api OAuth may open a browser once).")
    try:
        hits = digikey_keyword_search("resistor", 10)
    except DigiKeyConfigurationError as e:
        print(f"CONFIG ERROR: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        sys.exit(1)

    print(f"Received {len(hits)} candidate(s).")
    if hits:
        print("First candidate keys:", sorted(hits[0].keys()))
        for k in (
            "mpn",
            "digikey_part_number",
            "unit_price",
            "stock",
            "lead_time_weeks",
            "product_url",
        ):
            print(f"  {k}: {hits[0].get(k)}")
    else:
        print("No hits (API may have failed — see WARNING lines above).")


if __name__ == "__main__":
    main()
