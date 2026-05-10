#!/usr/bin/env python3
"""
DigiKey Third-Party MyLists smoke test (no auth).

POSTs a JSON **array** of parts to https://www.digikey.com/mylists/api/thirdparty
with ``listName`` and ``tags`` on the query string (same pattern as Digi-Key’s
KiCad-Push-to-DigiKey). The response is usually a JSON **string** containing a
``https://www.digikey.com/short/…`` one-time link — open it in a browser to
load the list and add to cart.

Optional env: ``DIGIKEY_MYLIST_TAGS`` (default ``BOMA``) for DigiKey’s tags query param.

Run from repository root:
  python bom_supplier_connector/test_digikey_mylists.py
  python bom_supplier_connector/test_digikey_mylists.py --part RMCF0603FG10K0CT-ND
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Default: common 10 kΩ 0603 resistor (exists on DigiKey production catalog).
DEFAULT_DKPN = "RMCF0603FG10K0CT-ND"


def main() -> None:
    from bom_supplier_connector.digikey_lists import DigiKeyListError, create_list_with_parts

    parser = argparse.ArgumentParser(
        description="DigiKey third-party MyList smoke test (single-use URL)."
    )
    parser.add_argument(
        "--part",
        default=os.getenv("DIGIKEY_MYLISTS_TEST_PART", DEFAULT_DKPN),
        help=f"DigiKey part number to add (default: {DEFAULT_DKPN}).",
    )
    parser.add_argument(
        "--list-name",
        default="BOMA Automated BOM",
        help='Value for JSON "listName" (default: BOMA Automated BOM).',
    )
    parser.add_argument(
        "--qty",
        type=int,
        default=1,
        help="Quantity for the test line (default: 1).",
    )
    args = parser.parse_args()

    parts = [
        {
            "part_number": args.part,
            "quantity": args.qty,
            "designator": "TEST1",
            "notes": "bom_supplier_connector/test_digikey_mylists.py",
        }
    ]

    print(f"Posting third-party MyList {args.list_name!r} with part {args.part!r} (qty {args.qty}) ...")
    try:
        info = create_list_with_parts(list_name=args.list_name, parts=parts)
    except DigiKeyListError as e:
        print(f"Error: {e}")
        raise SystemExit(1) from e

    url = info.get("single_use_url") or info.get("list_url") or ""
    print("\nSuccess.\n")
    print("=" * 72)
    print("OPEN THIS ONE-TIME LINK (DigiKey short URL; loads list → add to cart):")
    print("=" * 72)
    print(url)
    print("=" * 72)
    print(f"\nLines sent: {info.get('added_count')}  skipped (no PN): {info.get('skipped_count')}")


if __name__ == "__main__":
    main()
