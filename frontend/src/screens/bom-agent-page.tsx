"use client";

import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { Button } from "@/components/ui/button";
import { useRef, useState } from "react";
import {
  Upload,
  FileSpreadsheet,
  Sparkles,
  ShoppingCart,
  ExternalLink,
  Loader2,
} from "lucide-react";

type Row = {
  part: string;
  desc: string;
  qty: number;
  distributor: "DigiKey" | "Mouser";
  unit: number;
  stock: number;
  eta: string;
  url: string;
};

const MOCK_ROWS: Row[] = [
  {
    part: "STM32H743VIT6",
    desc: "Microcontroller chip",
    qty: 2,
    distributor: "DigiKey",
    unit: 14.62,
    stock: 1284,
    eta: "Ships May 12",
    url: "#",
  },
  {
    part: "TMC2209-LA-T",
    desc: "Motor driver",
    qty: 6,
    distributor: "Mouser",
    unit: 6.85,
    stock: 412,
    eta: "Ships May 12",
    url: "#",
  },
  {
    part: "BNO085",
    desc: "Motion sensor",
    qty: 1,
    distributor: "DigiKey",
    unit: 24.95,
    stock: 88,
    eta: "Ships May 13",
    url: "#",
  },
  {
    part: "INA226AIDGSR",
    desc: "Power monitor chip",
    qty: 4,
    distributor: "Mouser",
    unit: 3.42,
    stock: 2310,
    eta: "Ships May 12",
    url: "#",
  },
  {
    part: "LM2596S-5.0",
    desc: "Voltage regulator",
    qty: 3,
    distributor: "DigiKey",
    unit: 2.18,
    stock: 5612,
    eta: "Ships May 12",
    url: "#",
  },
  {
    part: "USB4500-03-A",
    desc: "USB-C connector",
    qty: 2,
    distributor: "Mouser",
    unit: 1.04,
    stock: 9821,
    eta: "Ships May 12",
    url: "#",
  },
];

export function BomAgentPage() {
  const [file, setFile] = useState<File | null>(null);
  const [running, setRunning] = useState(false);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const onFile = (f: File | undefined | null) => {
    if (!f) return;
    setFile(f);
    setRows(null);
  };

  const runAgent = async () => {
    if (!file) return;
    setRunning(true);
    setRows(null);
    await new Promise((r) => setTimeout(r, 1600));
    setRows(MOCK_ROWS);
    setRunning(false);
  };

  const subtotal = rows?.reduce((s, r) => s + r.qty * r.unit, 0) ?? 0;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <section className="mx-auto w-full max-w-6xl px-6 pt-12 pb-6">
        <p className="font-mono text-xs text-primary uppercase tracking-widest">Agent</p>
        <h1 className="mt-2 font-display text-4xl md:text-5xl text-gradient">
          Run BOMA on your list.
        </h1>
        <p className="mt-3 text-muted-foreground max-w-2xl">
          Upload a spreadsheet. We&apos;ll search DigiKey and Mouser for every part and build one
          priced cart.
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
            className={`rounded-2xl border-2 border-dashed p-10 text-center transition-colors ${
              drag ? "border-primary bg-primary/5" : "border-border bg-card"
            }`}
          >
            <div className="mx-auto h-12 w-12 rounded-xl bg-surface-2 flex items-center justify-center text-primary">
              <Upload className="h-6 w-6" />
            </div>
            <p className="mt-4 text-sm">
              {file ? (
                <span className="font-mono">{file.name}</span>
              ) : (
                <>Drag and drop your parts list here, or</>
              )}
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <Button variant="glass" size="sm" onClick={() => inputRef.current?.click()}>
                <FileSpreadsheet className="h-4 w-4" /> Choose file
              </Button>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.xls,.xlsx,text/csv"
                hidden
                onChange={(e) => onFile(e.target.files?.[0])}
              />
              <Button variant="hero" size="sm" disabled={!file || running} onClick={runAgent}>
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
                <div>→ searching Mouser…</div>
                <div className="text-foreground">→ picking the best match for each part…</div>
                <div className="shimmer h-px mt-3" />
              </div>
            </div>
          )}

          {rows && (
            <div className="rounded-2xl border border-border bg-card shadow-card overflow-hidden">
              <div className="px-6 py-4 border-b border-border flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold">Cart</h2>
                  <p className="text-xs text-muted-foreground font-mono">
                    {rows.length} items · ships by Tue, May 13
                  </p>
                </div>
                <Button variant="hero" size="sm">
                  <ShoppingCart className="h-4 w-4" /> Export cart
                </Button>
              </div>
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
                    {rows.map((r) => (
                      <tr
                        key={r.part}
                        className="border-b border-border/60 last:border-0 hover:bg-surface-2/50"
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
                          <a href={r.url} className="text-muted-foreground hover:text-primary">
                            <ExternalLink className="h-4 w-4" />
                          </a>
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
          <div className="rounded-2xl border border-border bg-card p-5 shadow-card">
            <h3 className="text-sm font-semibold">Sources</h3>
            <ul className="mt-3 space-y-2 text-sm font-mono">
              <li className="flex items-center justify-between">
                <span>DigiKey</span>
                <span className="h-2 w-2 rounded-full bg-primary" />
              </li>
              <li className="flex items-center justify-between">
                <span>Mouser</span>
                <span className="h-2 w-2 rounded-full bg-primary" />
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
          <div className="rounded-2xl border border-border bg-card p-5 shadow-card">
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
