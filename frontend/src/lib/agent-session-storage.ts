import type { DigikeyListPart } from "@/lib/agent-api";
import type { BomCartRow } from "@/lib/bom-types";

// Bumped to v2: old sessions stored a single-use ``listUrl`` which gets
// consumed by browser prefetch/preview. v2 stores the regen payload
// (``listParts``) so the page can mint a fresh URL on every click.
const STORAGE_KEY = "boma-agent-session-v2";

export type AgentSessionPayload = {
  v: 2;
  rows: BomCartRow[];
  displayCaption: string | null;
  listParts: DigikeyListPart[] | null;
  listName: string | null;
  listError: string | null;
  runError: string | null;
};

function isPayload(x: unknown): x is AgentSessionPayload {
  if (!x || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    o.v === 2 &&
    Array.isArray(o.rows) &&
    (o.displayCaption === null || typeof o.displayCaption === "string") &&
    (o.listParts === null || Array.isArray(o.listParts)) &&
    (o.listName === null || typeof o.listName === "string") &&
    (o.listError === null || typeof o.listError === "string") &&
    (o.runError === null || typeof o.runError === "string")
  );
}

export function readAgentSession(): AgentSessionPayload | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!isPayload(parsed)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeAgentSession(payload: Omit<AgentSessionPayload, "v">): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ v: 2, ...payload } satisfies AgentSessionPayload),
    );
  } catch {
    /* quota / private mode */
  }
}

export function clearAgentSession(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem("boma-agent-session-v1");
  } catch {
    /* ignore */
  }
}
