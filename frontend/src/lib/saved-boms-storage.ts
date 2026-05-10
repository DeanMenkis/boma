import type { SavedBom } from "@/lib/bom-types";

const STORAGE_PREFIX = "boma_saved_boms";

function storageKey(uid: string): string {
  return `${STORAGE_PREFIX}:${uid}`;
}

function readRaw(uid: string): SavedBom[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey(uid));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isSavedBom);
  } catch {
    return [];
  }
}

function isSavedBom(x: unknown): x is SavedBom {
  if (!x || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.title === "string" &&
    (o.sourceFileName === null || typeof o.sourceFileName === "string") &&
    typeof o.savedAt === "string" &&
    typeof o.lineCount === "number" &&
    typeof o.subtotal === "number" &&
    Array.isArray(o.rows)
  );
}

export function listSavedBoms(uid: string): SavedBom[] {
  return readRaw(uid).sort((a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime());
}

export function getSavedBom(uid: string, id: string): SavedBom | null {
  return readRaw(uid).find((b) => b.id === id) ?? null;
}

export function upsertSavedBom(uid: string, bom: SavedBom): void {
  const existing = readRaw(uid).filter((b) => b.id !== bom.id);
  existing.unshift(bom);
  window.localStorage.setItem(storageKey(uid), JSON.stringify(existing));
}

export function removeSavedBom(uid: string, id: string): void {
  const next = readRaw(uid).filter((b) => b.id !== id);
  window.localStorage.setItem(storageKey(uid), JSON.stringify(next));
}
