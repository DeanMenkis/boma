"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import {
  motion,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
  type MotionValue,
} from "motion/react";
import {
  Activity,
  ArrowRight,
  Check,
  CircuitBoard,
  ShoppingCart,
  Sparkles,
  Truck,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  MARKETING_BOM as BOM,
  MARKETING_BOM_LINE_COUNT,
  MARKETING_BOM_SUBTOTAL,
  MARKETING_BOM_UNIT_COUNT,
  formatMarketingCurrency,
  type MarketingBomRow,
} from "@/lib/marketing-bom";

const HERO_INDEX = 2;
const HERO_ROW = BOM[HERO_INDEX];

const STEPS = [
  { label: "Upload", icon: Upload, range: [0.0, 0.18] as const },
  { label: "Match", icon: Sparkles, range: [0.32, 0.7] as const },
  { label: "Cart", icon: ShoppingCart, range: [0.78, 1.0] as const },
];

export function ScrollDemo() {
  const reduce = useReducedMotion();
  if (reduce) return <ScrollDemoStatic />;
  return <ScrollDemoAnimated />;
}

function ScrollDemoAnimated() {
  const ref = useRef<HTMLDivElement | null>(null);

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });

  const progress = useSpring(scrollYProgress, {
    stiffness: 110,
    damping: 28,
    mass: 0.4,
  });

  // Header reveal
  const headerOpacity = useTransform(progress, [0, 0.05, 0.95, 1], [0, 1, 1, 0.7]);
  const headerY = useTransform(progress, [0, 0.05], [24, 0]);

  // Spreadsheet rises
  const sheetOpacity = useTransform(progress, [0, 0.06, 0.14], [0, 0.6, 1]);
  const sheetY = useTransform(progress, [0, 0.14], [60, 0]);

  // Target row highlight + lift
  const targetGlow = useTransform(progress, [0.18, 0.3], [0, 1]);
  const targetScale = useTransform(progress, [0.18, 0.3, 0.34], [1, 1.02, 1]);
  const otherDim = useTransform(progress, [0.18, 0.3, 0.86, 0.94], [1, 0.4, 0.4, 1]);
  // Source row goes "ghost" once the floating copy detaches
  const sourceGhost = useTransform(progress, [0.32, 0.36, 0.86, 0.92], [1, 0.18, 0.18, 1]);

  // Floating row — crosses the visualization
  const floatLeft = useTransform(progress, [0.3, 0.55, 0.86], ["6%", "44%", "72%"]);
  const floatTop = useTransform(progress, [0.3, 0.55, 0.86], ["48%", "36%", "44%"]);
  const floatScale = useTransform(progress, [0.3, 0.45, 0.7, 0.86], [1, 1.06, 1.04, 0.94]);
  const floatOpacity = useTransform(progress, [0.3, 0.34, 0.86, 0.92], [0, 1, 1, 0]);
  const floatRotate = useTransform(progress, [0.3, 0.55, 0.86], [-1, 1, -0.5]);

  // Match chips appear mid-flight
  const chipsOpacity = useTransform(progress, [0.42, 0.55, 0.78, 0.86], [0, 1, 1, 0]);
  const chipsY = useTransform(progress, [0.42, 0.55], [12, 0]);
  const priceOpacity = useTransform(progress, [0.5, 0.62, 0.78, 0.86], [0, 1, 1, 0]);
  const priceY = useTransform(progress, [0.5, 0.62], [12, 0]);

  // Cart panel
  const cartOpacity = useTransform(progress, [0.1, 0.25], [0, 1]);
  const cartY = useTransform(progress, [0.1, 0.25], [40, 0]);
  const cartGlow = useTransform(progress, [0.85, 1], [0, 1]);
  const dockedOpacity = useTransform(progress, [0.86, 0.94], [0, 1]);
  const dockedY = useTransform(progress, [0.86, 0.94], [16, 0]);

  // Total tally
  const totalNumber = useTransform(progress, [0.85, 1], [0, MARKETING_BOM_SUBTOTAL]);
  const [totalText, setTotalText] = useState(formatMarketingCurrency(0));
  useMotionValueEvent(totalNumber, "change", (v) => {
    setTotalText(formatMarketingCurrency(v));
  });

  // Checkout CTA
  const checkoutOpacity = useTransform(progress, [0.92, 1], [0, 1]);
  const checkoutScale = useTransform(progress, [0.92, 1], [0.96, 1]);

  return (
    <section ref={ref} className="relative h-[420vh]">
      <div className="sticky top-0 h-screen overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-40" />

        <div className="relative mx-auto flex h-full max-w-7xl flex-col px-6 pt-20 pb-10">
          {/* Header */}
          <motion.div style={{ opacity: headerOpacity, y: headerY }} className="text-center">
            <p className="font-mono text-xs uppercase tracking-widest text-primary">
              Live workflow
            </p>
            <h2 className="mt-3 font-display text-4xl md:text-5xl text-gradient">
              From spreadsheet to checkout, automatically.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground">
              Watch a single line travel from your BOM through DigiKey into a priced cart. Scroll to
              play.
            </p>
          </motion.div>

          {/* Step pills */}
          <ProgressPills progress={progress} />

          {/* Stage */}
          <div className="relative mt-6 grid flex-1 grid-cols-1 gap-6 md:grid-cols-5">
            {/* Spreadsheet */}
            <motion.div style={{ opacity: sheetOpacity, y: sheetY }} className="md:col-span-3">
              <SpreadsheetCard
                otherDim={otherDim}
                targetGlow={targetGlow}
                targetScale={targetScale}
                sourceGhost={sourceGhost}
              />
            </motion.div>

            {/* Cart */}
            <motion.div style={{ opacity: cartOpacity, y: cartY }} className="md:col-span-2">
              <CartCard
                dockedOpacity={dockedOpacity}
                dockedY={dockedY}
                cartGlow={cartGlow}
                checkoutOpacity={checkoutOpacity}
                checkoutScale={checkoutScale}
                totalText={totalText}
              />
            </motion.div>

            {/* Floating row */}
            <motion.div
              aria-hidden
              style={{
                left: floatLeft,
                top: floatTop,
                scale: floatScale,
                opacity: floatOpacity,
                rotate: floatRotate,
              }}
              className="pointer-events-none absolute z-20 hidden -translate-x-1/2 -translate-y-1/2 md:block"
            >
              <FloatingRow
                row={HERO_ROW}
                chipsOpacity={chipsOpacity}
                chipsY={chipsY}
                priceOpacity={priceOpacity}
                priceY={priceY}
              />
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* --- Sub-components ---------------------------------------------------- */

function ProgressPills({ progress }: { progress: MotionValue<number> }) {
  return (
    <div className="mt-8 flex items-center justify-center gap-2 font-mono text-xs">
      {STEPS.map((step, i) => (
        <Pill key={step.label} step={step} progress={progress} index={i} />
      ))}
    </div>
  );
}

function Pill({
  step,
  progress,
  index,
}: {
  step: (typeof STEPS)[number];
  progress: MotionValue<number>;
  index: number;
}) {
  const [start, end] = step.range;
  const active = useTransform(progress, [start - 0.02, start, end, end + 0.05], [0, 1, 1, 0.5]);
  const pillOpacity = useTransform(active, [0, 1], [0.4, 1]);
  const Icon = step.icon;
  return (
    <>
      {index > 0 && <div className="h-px w-6 bg-border md:w-10" />}
      <motion.div
        style={{ opacity: pillOpacity }}
        className="flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5"
      >
        <motion.span
          style={{ opacity: active }}
          className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground"
        >
          <Icon className="h-3 w-3" />
        </motion.span>
        <span className="text-foreground">{step.label}</span>
      </motion.div>
    </>
  );
}

function SpreadsheetCard({
  otherDim,
  targetGlow,
  targetScale,
  sourceGhost,
}: {
  otherDim: MotionValue<number>;
  targetGlow: MotionValue<number>;
  targetScale: MotionValue<number>;
  sourceGhost: MotionValue<number>;
}) {
  const glowShadow = useTransform(
    targetGlow,
    [0, 1],
    [
      "0 0 0 0 rgba(0,0,0,0)",
      "0 0 0 1px color-mix(in oklab, var(--primary) 60%, transparent), 0 12px 40px -10px color-mix(in oklab, var(--primary) 50%, transparent)",
    ],
  );
  const ghostOverlay = useTransform(sourceGhost, (v) => 1 - v);

  return (
    <div className="rounded-2xl border border-border bg-card shadow-card overflow-hidden">
      {/* Sheet header */}
      <div className="flex items-center justify-between border-b border-border bg-surface-2 px-4 py-2.5">
        <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
          <span className="h-2.5 w-2.5 rounded-full bg-destructive/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-primary/70" />
          <span className="ml-2">bom_v3.xlsx</span>
        </div>
        <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Sheet1
        </div>
      </div>

      {/* Column header */}
      <div className="grid grid-cols-[40px_1fr_1.4fr_60px_80px] border-b border-border bg-surface px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
        <div>#</div>
        <div>Part</div>
        <div>Description</div>
        <div className="text-right">Qty</div>
        <div className="text-right">Unit</div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-border">
        {BOM.map((row, i) => {
          const isHero = i === HERO_INDEX;
          return (
            <motion.div
              key={row.part}
              style={{
                opacity: isHero ? 1 : otherDim,
                scale: isHero ? targetScale : 1,
                boxShadow: isHero ? glowShadow : undefined,
              }}
              className={cn(
                "relative grid grid-cols-[40px_1fr_1.4fr_60px_80px] items-center px-3 py-2.5 font-mono text-xs",
                isHero && "bg-surface-2/60",
              )}
            >
              <div className="text-muted-foreground">{i + 1}</div>
              <div className="truncate text-foreground">{row.part}</div>
              <div className="truncate text-muted-foreground">{row.desc}</div>
              <div className="text-right text-foreground">{row.qty}</div>
              <div className="text-right text-muted-foreground">${row.unit.toFixed(2)}</div>

              {/* Ghost overlay when source row is "extracted" */}
              {isHero && (
                <motion.div
                  style={{ opacity: ghostOverlay }}
                  className="pointer-events-none absolute inset-1 rounded-md border border-dashed border-primary/50 bg-primary/5"
                />
              )}
            </motion.div>
          );
        })}
      </div>

      <div className="flex items-center justify-between border-t border-border bg-surface px-4 py-2 font-mono text-[10px] text-muted-foreground">
        <span>
          {MARKETING_BOM_LINE_COUNT} line items · {MARKETING_BOM_UNIT_COUNT.toLocaleString()} units
        </span>
        <span className="flex items-center gap-1">
          <Activity className="h-3 w-3 text-primary" />
          Live distributor pricing
        </span>
      </div>
    </div>
  );
}

function FloatingRow({
  row,
  chipsOpacity,
  chipsY,
  priceOpacity,
  priceY,
}: {
  row: MarketingBomRow;
  chipsOpacity: MotionValue<number>;
  chipsY: MotionValue<number>;
  priceOpacity: MotionValue<number>;
  priceY: MotionValue<number>;
}) {
  return (
    <div className="relative">
      <div
        className="rounded-xl border border-primary/40 bg-card px-4 py-3 font-mono text-xs shadow-glow"
        style={{ minWidth: 280 }}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="truncate">
            <div className="text-foreground">{row.part}</div>
            <div className="truncate text-[10px] text-muted-foreground">{row.desc}</div>
          </div>
          <div className="rounded-md border border-border bg-surface px-2 py-0.5 text-[10px] text-muted-foreground">
            qty {row.qty}
          </div>
        </div>
      </div>

      {/* Match chips below */}
      <motion.div
        style={{ opacity: chipsOpacity, y: chipsY }}
        className="mt-2 flex items-center justify-center gap-2 font-mono text-[10px]"
      >
        <span className="rounded-full border border-border bg-surface px-2 py-1 text-muted-foreground">
          <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-red-400" />
          DigiKey
        </span>
      </motion.div>

      {/* Price + stock */}
      <motion.div
        style={{ opacity: priceOpacity, y: priceY }}
        className="mt-2 flex items-center justify-center gap-2 font-mono text-[10px]"
      >
        <span className="rounded-md bg-primary/15 px-2 py-1 text-primary">
          ${row.unit.toFixed(2)} · best
        </span>
        <span className="rounded-md border border-border bg-surface px-2 py-1 text-muted-foreground">
          12,480 in stock
        </span>
      </motion.div>
    </div>
  );
}

function CartLineRows({
  dockedOpacity,
  dockedY,
}: {
  dockedOpacity: MotionValue<number>;
  dockedY: MotionValue<number>;
}) {
  const heroPresence = useTransform(dockedOpacity, [0, 1], [0.35, 1]);

  return (
    <>
      {BOM.map((row, i) => {
        const isHero = i === HERO_INDEX;
        if (!isHero) {
          return (
            <div
              key={row.part}
              className="flex items-center justify-between rounded-md border border-border bg-surface px-3 py-2 font-mono text-[11px]"
            >
              <div className="truncate text-muted-foreground">{row.part}</div>
              <div className="text-muted-foreground">
                {row.qty} × ${row.unit.toFixed(2)}
              </div>
            </div>
          );
        }
        return (
          <motion.div
            key={row.part}
            style={{ opacity: heroPresence, y: dockedY }}
            className="flex items-center justify-between rounded-md border border-primary/40 bg-primary/10 px-3 py-2 font-mono text-[11px]"
          >
            <div className="flex items-center gap-2 truncate text-foreground">
              <Check className="h-3 w-3 text-primary" />
              {row.part}
            </div>
            <div className="text-foreground">
              {row.qty} × ${row.unit.toFixed(2)}
            </div>
          </motion.div>
        );
      })}
    </>
  );
}

function CartCard({
  dockedOpacity,
  dockedY,
  cartGlow,
  checkoutOpacity,
  checkoutScale,
  totalText,
}: {
  dockedOpacity: MotionValue<number>;
  dockedY: MotionValue<number>;
  cartGlow: MotionValue<number>;
  checkoutOpacity: MotionValue<number>;
  checkoutScale: MotionValue<number>;
  totalText: string;
}) {
  const cartShadow = useTransform(
    cartGlow,
    [0, 1],
    [
      "0 1px 0 0 oklch(1 0 0 / 6%) inset, 0 20px 60px -30px oklch(0 0 0 / 60%)",
      "0 1px 0 0 oklch(1 0 0 / 6%) inset, 0 0 0 1px color-mix(in oklab, var(--primary) 30%, transparent), 0 30px 80px -20px color-mix(in oklab, var(--primary) 35%, transparent)",
    ],
  );

  return (
    <motion.div
      style={{ boxShadow: cartShadow }}
      className="flex h-full flex-col rounded-2xl border border-border bg-card p-5"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-surface-2 text-primary">
            <ShoppingCart className="h-4 w-4" />
          </div>
          <div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
              Cart
            </div>
            <div className="text-sm">Live · DigiKey</div>
          </div>
        </div>
        <div className="rounded-md border border-border bg-surface px-2 py-1 font-mono text-[10px] text-muted-foreground">
          {MARKETING_BOM_LINE_COUNT} lines
        </div>
      </div>

      {/* Cart lines — same order as the BOM */}
      <div className="mt-4 space-y-2">
        <CartLineRows dockedOpacity={dockedOpacity} dockedY={dockedY} />
      </div>

      {/* Footer summary */}
      <div className="mt-auto pt-5">
        <div className="flex items-center justify-between border-t border-border pt-4 font-mono text-xs">
          <span className="flex items-center gap-2 text-muted-foreground">
            <Truck className="h-3 w-3" />
            Ships in 3 days
          </span>
          <span className="flex items-center gap-2 text-muted-foreground">
            <CircuitBoard className="h-3 w-3" />
            {MARKETING_BOM_UNIT_COUNT.toLocaleString()} units
          </span>
        </div>

        <div className="mt-3 flex items-end justify-between">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Subtotal
            </div>
            <div className="font-display text-3xl text-gradient tabular-nums">{totalText}</div>
          </div>
        </div>

        <motion.div style={{ opacity: checkoutOpacity, scale: checkoutScale }} className="mt-4">
          <Link href="/app">
            <Button variant="hero" size="lg" className="w-full">
              Ready to checkout <ArrowRight />
            </Button>
          </Link>
        </motion.div>
      </div>
    </motion.div>
  );
}

/* --- Reduced motion fallback ------------------------------------------ */

function ScrollDemoStatic() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <div className="text-center">
        <p className="font-mono text-xs uppercase tracking-widest text-primary">Live workflow</p>
        <h2 className="mt-3 font-display text-4xl md:text-5xl text-gradient">
          From spreadsheet to checkout, automatically.
        </h2>
      </div>

      <div className="mt-12 grid gap-6 md:grid-cols-3">
        {[
          {
            icon: Upload,
            title: "Upload your list",
            body: "Drop a spreadsheet of part numbers, quantities, and notes.",
          },
          {
            icon: Sparkles,
            title: "Match every part",
            body: "We search DigiKey and pick the best in-stock option for each line.",
          },
          {
            icon: ShoppingCart,
            title: "Get a priced cart",
            body: "One cart, one shipping date, and per-line pricing ready to checkout.",
          },
        ].map(({ icon: Icon, title, body }) => (
          <div key={title} className="rounded-xl border border-border bg-card p-6 shadow-card">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-2 text-primary">
              <Icon className="h-5 w-5" />
            </div>
            <h3 className="mt-5 text-lg font-semibold">{title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ScrollDemo;
