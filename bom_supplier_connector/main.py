#!/usr/bin/env python3
"""
CLI for BOM enrichment.

Usage (from repository root):
  python bom_supplier_connector/main.py path/to/bom.csv --deadline 30

If no CSV path is given, runs a built-in 3-row test (requires CLOD_API_KEY).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bom_supplier_connector.pipeline import enrich_bom, enrich_bom_rows  # noqa: E402


def _builtin_rows() -> list[dict]:
    return [
        {
            "id": 1,
            "name": "10nF",
            "designator": "C1",
            "footprint": "C0805",
            "quantity": 1,
            "mpn": "",
            "manufacturer": "",
            "supplier": "",
            "supplier_part": "",
            "existing_price": 0.0,
        },
        {
            "id": 2,
            "name": "TMC2209",
            "designator": "U1",
            "footprint": "TMC2209",
            "quantity": 5,
            "mpn": "TMC2209",
            "manufacturer": "",
            "supplier": "",
            "supplier_part": "",
            "existing_price": 0.0,
        },
        {
            "id": 3,
            "name": "AP64501SP-13",
            "designator": "U2",
            "footprint": "",
            "quantity": 1,
            "mpn": "AP64501SP-13",
            "manufacturer": "",
            "supplier": "",
            "supplier_part": "C2071517",
            "existing_price": 0.0,
        },
    ]


def _print_table(console: Console, result: dict) -> None:
    table = Table(title="BOM enrichment")
    for col in (
        "Name",
        "Qty",
        "Matched MPN",
        "Unit Price",
        "Total",
        "Stock",
        "Lead Time",
        "Meets Deadline",
    ):
        table.add_column(col)

    for p in result["parts"]:
        meets = p.get("meets_deadline")
        cell = Text("yes" if meets else "no", style="green" if meets else "red")
        table.add_row(
            str(p.get("name", "")),
            str(p.get("quantity", "")),
            str(p.get("matched_mpn", "")),
            f"${float(p.get('unit_price') or 0):.4f}",
            f"${float(p.get('total_price') or 0):.2f}",
            str(p.get("stock", "")),
            f"{float(p.get('lead_time_weeks') or 0):.1f} wk",
            cell,
        )
    console.print(table)


def _print_warnings(console: Console, result: dict) -> None:
    bad = [p for p in result["parts"] if not p.get("meets_deadline")]
    if not bad:
        return
    console.print("\n[bold yellow]WARNINGS[/bold yellow]")
    for p in bad:
        w = p.get("deadline_warning") or "Cannot meet project deadline."
        console.print(f"  - Row {p.get('id')} ({p.get('name')}): {w}")


def _print_summary(console: Console, result: dict) -> None:
    s = result["summary"]
    console.print("\n[bold]Summary[/bold]")
    console.print(json.dumps(s, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich a BOM via DigiKey + CLōD agents.")
    parser.add_argument("csv_filepath", nargs="?", help="Path to BOM CSV")
    parser.add_argument(
        "--deadline",
        type=int,
        default=None,
        help="Project deadline in days. Omit to ignore deadline and pick cheapest.",
    )
    args = parser.parse_args()
    console = Console()

    try:
        if args.csv_filepath:
            result = enrich_bom(args.csv_filepath, args.deadline)
        else:
            console.print(
                "[dim]No CSV provided — running built-in test (3 rows, no deadline).[/dim]\n"
            )
            result = enrich_bom_rows(_builtin_rows(), args.deadline)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e

    _print_table(console, result)
    _print_warnings(console, result)
    _print_summary(console, result)
    console.print(
        "\n[dim]DigiKey third-party MyLists (single-use URL) are created from the "
        "FastAPI POST /enrich flow when rows include DigiKey part numbers.[/dim]"
    )


if __name__ == "__main__":
    main()
