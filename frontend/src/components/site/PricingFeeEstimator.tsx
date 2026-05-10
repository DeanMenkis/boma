"use client";

import { useMemo, useState } from "react";
import { Label } from "@/components/ui/label";
import { BOMA_BASE_FEE_USD, BOMA_PER_LINE_USD, computeBomaFeeUsd } from "@/lib/pricing";

function formatUsd(n: number) {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function PricingFeeEstimator() {
  const [lines, setLines] = useState(24);

  const fee = useMemo(() => computeBomaFeeUsd(lines), [lines]);

  return (
    <div className="rounded-xl border border-border bg-muted/30 p-6">
      <p className="font-mono text-xs text-primary uppercase tracking-widest">Estimate your fee</p>
      <p className="mt-2 text-sm text-muted-foreground">
        Lines are rows in your uploaded CSV (your BOM line count).
      </p>
      <div className="mt-5 space-y-2">
        <Label htmlFor="bom-lines" className="text-sm font-normal text-foreground">
          BOM lines
        </Label>
        <input
          id="bom-lines"
          type="number"
          inputMode="numeric"
          min={0}
          step={1}
          value={Number.isFinite(lines) ? lines : 0}
          onChange={(e) => {
            const v = parseInt(e.target.value, 10);
            setLines(Number.isFinite(v) ? Math.max(0, v) : 0);
          }}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 font-mono"
        />
      </div>
      <div className="mt-6 rounded-lg border border-border bg-card p-4">
        <p className="text-xs font-mono text-muted-foreground uppercase tracking-wide">
          BOMA fee (USD)
        </p>
        <p className="mt-1 font-display text-3xl tabular-nums">{formatUsd(fee)}</p>
        <p className="mt-2 text-xs text-muted-foreground font-mono">
          {formatUsd(BOMA_BASE_FEE_USD)} + {lines} × {formatUsd(BOMA_PER_LINE_USD)}
        </p>
      </div>
    </div>
  );
}
