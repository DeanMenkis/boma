import type { BomCartRow } from "@/lib/bom-types";

/**
 * Shape of one enriched part row returned by `POST /enrich`. Mirrors the
 * dict produced by `bom_supplier_connector.agents.specialist_agent`.
 */
export type EnrichedPart = {
  id?: number;
  name?: string;
  designator?: string;
  footprint?: string;
  quantity?: number;
  mpn?: string;
  manufacturer?: string;
  matched_mpn?: string;
  matched_description?: string;
  unit_price?: number;
  total_price?: number;
  stock?: number;
  lead_time_weeks?: number;
  estimated_arrival_days?: number;
  meets_deadline?: boolean;
  deadline_warning?: string | null;
  supplier_name?: string;
  buy_url?: string;
  digikey_part_number?: string;
  match_confidence?: "high" | "medium" | "low";
  match_reason?: string;
};

export type EnrichSummary = {
  total_parts: number;
  total_cost_usd: number;
  parts_found: number;
  parts_missing: number;
  parts_meeting_deadline: number;
  parts_missing_deadline: number;
  deadline_days: number | null;
};

/** Payload the backend hands back for re-generating DigiKey list URLs.
 * The frontend keeps this around and POSTs it to `/digikey/list` every time
 * the user wants a fresh single-use URL (the previous URL may have been
 * consumed by a browser prefetch / link preview). */
export type DigikeyListPart = {
  part_number: string;
  quantity: number;
  designator?: string;
  notes?: string;
};

export type EnrichResponse = {
  parts: EnrichedPart[];
  summary: EnrichSummary;
  deadline_days: number | null;
  total_cost_usd?: number;
  /** Pre-formatted payload — pass this to `createDigikeyList` on click. */
  list_parts?: DigikeyListPart[];
  list_name?: string;
  /** Present when no row in the BOM has a DigiKey part number. */
  digikey_list_error?: string;
};

function apiBase(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set — add it to frontend/.env.local",
    );
  }
  return url.replace(/\/+$/, "");
}

/** Calls `POST /enrich`. Throws on non-2xx with the backend's detail. */
export async function enrichBom(
  file: File,
  opts: { deadlineDays?: number; listName?: string; idToken?: string | null } = {},
): Promise<EnrichResponse> {
  const form = new FormData();
  form.append("file", file);
  if (opts.deadlineDays != null) {
    form.append("deadline_days", String(opts.deadlineDays));
  }
  if (opts.listName) form.append("list_name", opts.listName);

  const res = await fetch(`${apiBase()}/enrich`, {
    method: "POST",
    body: form,
    headers: opts.idToken ? { Authorization: `Bearer ${opts.idToken}` } : undefined,
  });

  if (!res.ok) {
    let detail = `Backend returned ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // Keep the status-code fallback.
    }
    throw new Error(detail);
  }
  return (await res.json()) as EnrichResponse;
}

/** Mint a fresh single-use DigiKey MyList URL for the given parts. */
export async function createDigikeyList(
  parts: DigikeyListPart[],
  listName?: string,
): Promise<{ list_url: string; added_count?: number; skipped_count?: number }> {
  const res = await fetch(`${apiBase()}/digikey/list`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parts, list_name: listName }),
  });
  if (!res.ok) {
    let detail = `Backend returned ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // keep status fallback
    }
    throw new Error(detail);
  }
  const data = (await res.json()) as {
    list_url?: string;
    added_count?: number;
    skipped_count?: number;
  };
  if (!data.list_url) {
    throw new Error("DigiKey returned no list URL.");
  }
  return {
    list_url: data.list_url,
    added_count: data.added_count,
    skipped_count: data.skipped_count,
  };
}

/** Convert an enriched part row into the cart-row shape the table expects. */
export function enrichedPartToCartRow(p: EnrichedPart): BomCartRow {
  const qty = Number(p.quantity ?? 1);
  const unit = Number(p.unit_price ?? 0);
  const part =
    (p.matched_mpn && p.matched_mpn.trim()) ||
    (p.mpn && p.mpn.trim()) ||
    (p.name && p.name.trim()) ||
    "(unmatched)";
  const desc =
    (p.matched_description && p.matched_description.trim()) ||
    [p.name, p.footprint].filter(Boolean).join(" · ") ||
    "—";
  const eta = formatEta(p);

  return {
    part,
    desc,
    qty,
    distributor: p.supplier_name || "DigiKey",
    unit,
    stock: Number(p.stock ?? 0),
    eta,
    url: p.buy_url || "#",
    digikeyPartNumber: p.digikey_part_number || undefined,
    matchConfidence: p.match_confidence,
  };
}

function formatEta(p: EnrichedPart): string {
  const days =
    Number.isFinite(Number(p.estimated_arrival_days)) &&
    Number(p.estimated_arrival_days) > 0
      ? Number(p.estimated_arrival_days)
      : Number(p.lead_time_weeks ?? 0) > 0
        ? Math.round(Number(p.lead_time_weeks) * 7 + 3)
        : null;

  if (days == null) return p.meets_deadline === false ? "Lead unknown" : "In stock";
  if (days <= 3) return "Ships in ~3 days";
  return `~${days} days`;
}
