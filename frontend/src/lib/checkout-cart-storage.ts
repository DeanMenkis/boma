import type { BomCartRow } from "@/lib/bom-types";

const STORAGE_KEY = "boma_pending_checkout_cart";

export type PendingCheckoutCart = {
  rows: BomCartRow[];
  subtotal: number;
  title?: string;
};

function isCartRow(x: unknown): x is BomCartRow {
  if (!x || typeof x !== "object") return false;
  const r = x as Record<string, unknown>;
  return (
    typeof r.part === "string" &&
    typeof r.desc === "string" &&
    typeof r.qty === "number" &&
    (r.distributor === "DigiKey" || r.distributor === "Mouser") &&
    typeof r.unit === "number" &&
    typeof r.stock === "number" &&
    typeof r.eta === "string" &&
    typeof r.url === "string"
  );
}

export function setPendingCheckoutCart(data: PendingCheckoutCart): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function getPendingCheckoutCart(): PendingCheckoutCart | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return null;
    const o = parsed as Record<string, unknown>;
    const rows = o.rows;
    if (!Array.isArray(rows) || !rows.length || !rows.every(isCartRow)) return null;
    const subtotal = o.subtotal;
    if (typeof subtotal !== "number") return null;
    const title = o.title;
    return {
      rows,
      subtotal,
      title: typeof title === "string" ? title : undefined,
    };
  } catch {
    return null;
  }
}

export function clearPendingCheckoutCart(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STORAGE_KEY);
}
