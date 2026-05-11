"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Bookmark,
  Check,
  ExternalLink,
  FileSpreadsheet,
  Loader2,
  ShoppingCart,
  Sparkles,
  Upload,
} from "lucide-react";

import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import { useSavedBoms } from "@/hooks/useSavedBoms";
import {
  createDigikeyList,
  enrichBom,
  enrichedPartToCartRow,
  type DigikeyListPart,
} from "@/lib/agent-api";
import type { BomCartRow, SavedBom } from "@/lib/bom-types";
import { setPendingCheckoutCart } from "@/lib/checkout-cart-storage";
import { getSavedBom } from "@/lib/saved-boms-storage";
import {
  clearAgentSession,
  readAgentSession,
  writeAgentSession,
} from "@/lib/agent-session-storage";

function getHydratedAgentState(): {
  rows: BomCartRow[] | null;
  sourceLabel: string | null;
  listParts: DigikeyListPart[] | null;
  listName: string | null;
  listError: string | null;
  runError: string | null;
} {
  const empty = {
    rows: null as BomCartRow[] | null,
    sourceLabel: null as string | null,
    listParts: null as DigikeyListPart[] | null,
    listName: null as string | null,
    listError: null as string | null,
    runError: null as string | null,
  };
  if (typeof window === "undefined") return empty;
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get("load")) return empty;
    const data = readAgentSession();
    if (!data) return empty;
    return {
      rows: data.rows?.length ? data.rows : null,
      sourceLabel: data.displayCaption,
      listParts: data.listParts?.length ? data.listParts : null,
      listName: data.listName,
      listError: data.listError,
      runError: data.runError,
    };
  } catch {
    return empty;
  }
}

export function BomAgentPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { saveSavedBom } = useSavedBoms(user?.uid ?? null);

  const [sessionSnap] = useState(() => getHydratedAgentState());

  const [file, setFile] = useState<File | null>(null);
  const [sourceLabel, setSourceLabel] = useState<string | null>(sessionSnap.sourceLabel);
  const [running, setRunning] = useState(false);
  const [rows, setRows] = useState<BomCartRow[] | null>(sessionSnap.rows);
  const [drag, setDrag] = useState(false);
  const [saveAcknowledged, setSaveAcknowledged] = useState(false);
  const [listParts, setListParts] = useState<DigikeyListPart[] | null>(
    sessionSnap.listParts,
  );
  const [listName, setListName] = useState<string | null>(sessionSnap.listName);
  const [listError, setListError] = useState<string | null>(sessionSnap.listError);
  const [openingList, setOpeningList] = useState(false);
  const [runError, setRunError] = useState<string | null>(sessionSnap.runError);
  const inputRef = useRef<HTMLInputElement>(null);
  const saveFlashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const onSavedBomLoaded = useCallback((bom: SavedBom) => {
    setRows(bom.rows);
    setSourceLabel(bom.title);
    setFile(null);
    setListParts(null);
    setListName(bom.title);
    setListError(null);
    setRunError(null);
  }, []);

  const onFile = (f: File | undefined | null) => {
    if (!f) return;
    setFile(f);
    setRows(null);
    setSourceLabel(null);
    setListParts(null);
    setListName(null);
    setListError(null);
    setRunError(null);
  };

  const runAgent = async () => {
    if (!file) return;
    setRunning(true);
    setRows(null);
    setListParts(null);
    setListName(null);
    setListError(null);
    setRunError(null);
    try {
      const baseName = file.name.replace(/\.[^.]+$/, "");
      const data = await enrichBom(file, { listName: baseName });
      const cartRows = (data.parts ?? []).map(enrichedPartToCartRow);
      setRows(cartRows);
      if (data.list_parts?.length) {
        setListParts(data.list_parts);
        setListName(data.list_name ?? baseName);
      } else if (data.digikey_list_error) {
        setListError(data.digikey_list_error);
      }
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Agent run failed.");
    } finally {
      setRunning(false);
    }
  };

  /**
   * Always mint a fresh DigiKey list URL on click. The third-party MyList
   * endpoint returns single-use URLs that get burned by browser prefetch
   * or link previews, so we never cache the URL itself — only the parts
   * payload, which can regenerate URLs indefinitely.
   */
  const openDigikeyList = async () => {
    if (!listParts?.length || openingList) return;
    setOpeningList(true);
    setListError(null);
    // Pre-open the tab synchronously so popup blockers don't reject it
    // once the fetch resolves a moment later.
    const popup = window.open("about:blank", "_blank", "noopener,noreferrer");
    try {
      const { list_url } = await createDigikeyList(listParts, listName ?? undefined);
      if (popup) {
        popup.location.href = list_url;
      } else {
        // Popup blocked — navigate in the current tab as fallback.
        window.location.href = list_url;
      }
    } catch (err) {
      if (popup) popup.close();
      setListError(
        err instanceof Error ? err.message : "Couldn't open DigiKey list.",
      );
    } finally {
      setOpeningList(false);
    }
  };

  const subtotal = rows?.reduce((s, r) => s + r.qty * r.unit, 0) ?? 0;

  useEffect(() => {
    return () => {
      if (saveFlashTimerRef.current) clearTimeout(saveFlashTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const caption = file?.name ?? sourceLabel;
    const hasCart = rows && rows.length > 0;
    if (hasCart) {
      writeAgentSession({
        rows: rows!,
        displayCaption: caption ?? null,
        listParts,
        listName,
        listError,
        runError,
      });
      return;
    }
    if (runError) {
      writeAgentSession({
        rows: [],
        displayCaption: caption ?? null,
        listParts,
        listName,
        listError,
        runError,
      });
      return;
    }
    clearAgentSession();
  }, [rows, file?.name, sourceLabel, listParts, listName, listError, runError]);

  const saveToProfile = useCallback(() => {
    if (!rows?.length || !user?.uid) return;
    const baseName =
      file?.name?.replace(/\.[^.]+$/, "") ??
      sourceLabel ??
      `Cart · ${new Date().toLocaleDateString()}`;
    const id =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `bom-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
    saveSavedBom({
      id,
      title: baseName,
      sourceFileName: file?.name ?? null,
      savedAt: new Date().toISOString(),
      lineCount: rows.length,
      subtotal,
      rows,
    });
    if (saveFlashTimerRef.current) clearTimeout(saveFlashTimerRef.current);
    setSaveAcknowledged(true);
    saveFlashTimerRef.current = setTimeout(() => {
      setSaveAcknowledged(false);
      saveFlashTimerRef.current = null;
    }, 800);
  }, [rows, user?.uid, file, sourceLabel, subtotal, saveSavedBom]);

  const uploadCaption = file?.name ?? sourceLabel;

  const exportToCheckout = useCallback(() => {
    if (!rows?.length) return;
    setPendingCheckoutCart({
      rows,
      subtotal,
      title: uploadCaption ?? undefined,
    });
    router.push("/app/checkout");
  }, [rows, subtotal, router, uploadCaption]);

  return (
    <div className="min-h-screen flex flex-col">
      <Suspense fallback={null}>
        <LoadSavedBomBridge onLoaded={onSavedBomLoaded} />
      </Suspense>

      <Header />

      <section className="mx-auto w-full max-w-6xl px-6 pt-12 pb-6">
        <p className="font-mono text-xs text-primary uppercase tracking-widest">Agent</p>
        <h1 className="mt-2 font-display text-4xl md:text-5xl text-gradient">
          Run BOMA on your list.
        </h1>
        <p className="mt-3 text-muted-foreground max-w-2xl">
          Upload a spreadsheet. We&apos;ll search DigiKey for every part and build one priced cart.
        </p>
      </section>

      <section className="mx-auto w-full max-w-6xl px-6 pb-12 grid lg:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-6">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              onFile(e.dataTransfer.files?.[0]);
            }}
            className={`group rounded-2xl border-2 border-dashed p-10 text-center cursor-default transition-all duration-200 ${
              drag
                ? "border-primary bg-primary/5 scale-[1.01] shadow-[0_0_24px_-8px_rgba(163,230,53,0.35)]"
                : "border-border bg-card hover:border-primary/45 hover:bg-card/95 hover:shadow-[0_8px_28px_-12px_rgba(0,0,0,0.45)]"
            }`}
          >
            <div className="mx-auto h-12 w-12 rounded-xl bg-surface-2 flex items-center justify-center text-primary transition-transform duration-200 group-hover:scale-105 group-hover:bg-primary/10">
              <Upload className="h-6 w-6" />
            </div>
            <p className="mt-4 text-sm">
              {uploadCaption ? (
                <span className="font-mono">{uploadCaption}</span>
              ) : (
                <>Drag and drop your parts list here, or</>
              )}
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <Button
                variant="glass"
                size="sm"
                onClick={() => inputRef.current?.click()}
                className="transition-all duration-200 hover:bg-primary/12 hover:ring-1 hover:ring-primary/30"
              >
                <FileSpreadsheet className="h-4 w-4" /> Choose file
              </Button>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.xls,.xlsx,text/csv"
                hidden
                onChange={(e) => onFile(e.target.files?.[0])}
              />
              <Button
                variant="hero"
                size="sm"
                disabled={!file || running}
                onClick={runAgent}
                className="transition-all duration-200 enabled:hover:brightness-110 enabled:hover:shadow-[0_0_24px_-6px_rgba(163,230,53,0.45)]"
              >
                {running ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                {running ? "Agent running…" : "Run agent"}
              </Button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground font-mono">.csv · .xlsx · max 10MB</p>
          </div>

          {running && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-card">
              <div className="font-mono text-sm space-y-1.5 text-muted-foreground">
                <div>→ reading your file…</div>
                <div>→ searching DigiKey…</div>
                <div className="text-foreground">→ picking the best match for each part…</div>
                <div>→ building DigiKey cart…</div>
                <div className="shimmer h-px mt-3" />
              </div>
            </div>
          )}

          {runError && !running && (
            <div className="rounded-2xl border border-destructive/40 bg-destructive/5 p-4 shadow-card">
              <div className="flex items-start gap-3 text-sm">
                <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" aria-hidden />
                <div>
                  <p className="font-semibold text-foreground">Agent run failed</p>
                  <p className="text-muted-foreground font-mono text-xs mt-1 break-words">
                    {runError}
                  </p>
                </div>
              </div>
            </div>
          )}

          {rows && (
            <div className="rounded-2xl border border-border bg-card shadow-card overflow-hidden">
              <div className="px-6 py-4 border-b border-border flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold">Cart</h2>
                  <p className="text-xs text-muted-foreground font-mono">
                    {rows.length} items
                    {listParts?.length ? ` · DigiKey list ready (${listParts.length})` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {user ? (
                    <Button
                      type="button"
                      variant="glass"
                      size="sm"
                      onClick={saveToProfile}
                      aria-live="polite"
                      className={cn(
                        "gap-1.5 transition-all duration-200 hover:bg-primary/12 hover:ring-1 hover:ring-primary/30",
                        saveAcknowledged && "save-to-profile-gold-flash",
                      )}
                    >
                      {saveAcknowledged ? (
                        <>
                          <Check className="h-4 w-4 text-amber-300" aria-hidden />
                          Saved to profile
                        </>
                      ) : (
                        <>
                          <Bookmark className="h-4 w-4" aria-hidden />
                          Save to profile
                        </>
                      )}
                    </Button>
                  ) : (
                    <Button
                      variant="glass"
                      size="sm"
                      asChild
                      className="transition-all duration-200 hover:bg-primary/12 hover:ring-1 hover:ring-primary/30"
                    >
                      <Link href="/login">Sign in to save</Link>
                    </Button>
                  )}
                  {listParts?.length ? (
                    <Button
                      variant="hero"
                      size="sm"
                      type="button"
                      onClick={openDigikeyList}
                      disabled={openingList}
                      className="transition-all duration-200 hover:brightness-110 hover:shadow-[0_0_22px_-6px_rgba(163,230,53,0.45)]"
                    >
                      {openingList ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <ExternalLink className="h-4 w-4" />
                      )}{" "}
                      {openingList ? "Opening…" : "Open list on DigiKey"}
                    </Button>
                  ) : null}
                  <Button
                    variant={listParts?.length ? "glass" : "hero"}
                    size="sm"
                    type="button"
                    onClick={exportToCheckout}
                    className={cn(
                      "transition-all duration-200",
                      listParts?.length
                        ? "hover:bg-primary/12 hover:ring-1 hover:ring-primary/30"
                        : "hover:brightness-110 hover:shadow-[0_0_22px_-6px_rgba(163,230,53,0.45)]",
                    )}
                  >
                    <ShoppingCart className="h-4 w-4" /> Export cart
                  </Button>
                </div>
              </div>
              {listError && (
                <div className="px-6 py-3 border-b border-border bg-amber-500/5 text-xs text-muted-foreground flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" aria-hidden />
                  <span>
                    Couldn&apos;t build a DigiKey list automatically:{" "}
                    <span className="font-mono">{listError}</span>
                  </span>
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-xs text-muted-foreground font-mono">
                    <tr className="border-b border-border">
                      <th className="text-left font-normal px-6 py-3">Part</th>
                      <th className="text-left font-normal px-3 py-3">Source</th>
                      <th className="text-right font-normal px-3 py-3">Qty</th>
                      <th className="text-right font-normal px-3 py-3">Unit</th>
                      <th className="text-right font-normal px-3 py-3">Total</th>
                      <th className="text-left font-normal px-3 py-3">ETA</th>
                      <th className="px-3 py-3" />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, idx) => (
                      <tr
                        key={`${r.part}-${idx}`}
                        className="border-b border-border/60 last:border-0 border-l-[3px] border-l-transparent transition-colors duration-200 hover:border-l-primary hover:bg-primary/[0.08]"
                      >
                        <td className="px-6 py-3">
                          <div className="font-mono text-foreground">{r.part}</div>
                          <div className="text-xs text-muted-foreground">{r.desc}</div>
                        </td>
                        <td className="px-3 py-3">
                          <span className="inline-block rounded-md bg-surface-2 px-2 py-0.5 text-xs font-mono">
                            {r.distributor}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-right font-mono">{r.qty}</td>
                        <td className="px-3 py-3 text-right font-mono">${r.unit.toFixed(2)}</td>
                        <td className="px-3 py-3 text-right font-mono text-foreground">
                          ${(r.qty * r.unit).toFixed(2)}
                        </td>
                        <td className="px-3 py-3 text-xs text-muted-foreground">{r.eta}</td>
                        <td className="px-3 py-3">
                          {r.url && r.url !== "#" ? (
                            <a
                              href={r.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex rounded-lg p-2 -m-1 text-muted-foreground transition-all duration-200 hover:bg-primary/15 hover:text-primary hover:scale-110 hover:shadow-[0_0_16px_-6px_rgba(163,230,53,0.35)]"
                              aria-label={`Open ${r.part} on supplier site`}
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          ) : (
                            <span className="text-muted-foreground/40">
                              <ExternalLink className="h-4 w-4" />
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-6 py-4 border-t border-border flex items-center justify-between">
                <span className="text-xs font-mono text-muted-foreground">Subtotal</span>
                <span className="font-mono text-lg">${subtotal.toFixed(2)}</span>
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-5 shadow-card transition-all duration-200 hover:border-primary/35 hover:shadow-[0_14px_44px_-18px_rgba(0,0,0,0.55)]">
            <h3 className="text-sm font-semibold">Sources</h3>
            <ul className="mt-3 space-y-2 text-sm font-mono">
              <li className="flex items-center justify-between">
                <span>DigiKey</span>
                <span className="h-2 w-2 rounded-full bg-primary" />
              </li>
              <li className="flex items-center justify-between text-muted-foreground">
                <span>Mouser</span>
                <span className="text-[10px]">soon</span>
              </li>
              <li className="flex items-center justify-between text-muted-foreground">
                <span>Arrow</span>
                <span className="text-[10px]">soon</span>
              </li>
              <li className="flex items-center justify-between text-muted-foreground">
                <span>LCSC</span>
                <span className="text-[10px]">soon</span>
              </li>
            </ul>
          </div>
          <div className="rounded-2xl border border-border bg-card p-5 shadow-card transition-all duration-200 hover:border-primary/35 hover:shadow-[0_14px_44px_-18px_rgba(0,0,0,0.55)]">
            <h3 className="text-sm font-semibold">Tips</h3>
            <ul className="mt-3 space-y-2 text-xs text-muted-foreground">
              <li>
                · Include a <span className="font-mono text-foreground">part number</span> column
                for best results.
              </li>
              <li>
                · A <span className="font-mono text-foreground">quantity</span> and{" "}
                <span className="font-mono text-foreground">description</span> help us pick the
                right one.
              </li>
              <li>· Got notes? We&apos;ll read those too.</li>
            </ul>
          </div>
        </aside>
      </section>

      <Footer />
    </div>
  );
}

function LoadSavedBomBridge({ onLoaded }: { onLoaded: (bom: SavedBom) => void }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user } = useAuth();
  const loadId = searchParams.get("load");

  useEffect(() => {
    if (!user?.uid || !loadId) return;
    const bom = getSavedBom(user.uid, loadId);
    if (!bom) {
      router.replace("/app");
      return;
    }
    onLoaded(bom);
    router.replace("/app");
  }, [user?.uid, loadId, onLoaded, router]);

  return null;
}
