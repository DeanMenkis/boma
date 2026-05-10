import type { BomCartRow } from "@/lib/bom-types";

const HEADERS = [
  "Part",
  "Description",
  "Qty",
  "Distributor",
  "Unit USD",
  "Line Total USD",
  "Stock",
  "ETA",
  "Product URL",
] as const;

function escapeCsvCell(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export function bomCartRowsToCsv(rows: BomCartRow[]): string {
  const lines: string[] = [HEADERS.join(",")];
  for (const r of rows) {
    const lineTotal = r.qty * r.unit;
    lines.push(
      [
        escapeCsvCell(r.part),
        escapeCsvCell(r.desc),
        String(r.qty),
        escapeCsvCell(r.distributor),
        r.unit.toFixed(2),
        lineTotal.toFixed(2),
        String(r.stock),
        escapeCsvCell(r.eta),
        escapeCsvCell(r.url),
      ].join(","),
    );
  }
  return lines.join("\r\n");
}

export function downloadBomCartCsv(rows: BomCartRow[], title?: string): void {
  const csv = bomCartRowsToCsv(rows);
  const slug =
    title
      ?.trim()
      .replace(/[^\w\-]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 48) || "cart";
  const date = new Date().toISOString().slice(0, 10);
  const filename = `boma-cart_${slug}_${date}.csv`;

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
