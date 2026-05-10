"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, Download, Loader2, ShoppingCart } from "lucide-react";

import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { downloadBomCartCsv } from "@/lib/bom-cart-csv";
import {
  clearPendingCheckoutCart,
  getPendingCheckoutCart,
  type PendingCheckoutCart,
} from "@/lib/checkout-cart-storage";
import { isTestCheckoutCoupon, TEST_CHECKOUT_COUPON } from "@/lib/checkout-coupon";

export function CheckoutPage() {
  const router = useRouter();
  const [cart, setCart] = useState<PendingCheckoutCart | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [couponInput, setCouponInput] = useState("");
  const [couponError, setCouponError] = useState<string | null>(null);
  const [csvComplete, setCsvComplete] = useState(false);

  useEffect(() => {
    const data = getPendingCheckoutCart();
    if (!data?.rows?.length) {
      router.replace("/app");
      return;
    }
    setCart(data);
    setHydrated(true);
  }, [router]);

  const runTestCouponExport = useCallback(
    (payload: PendingCheckoutCart) => {
      downloadBomCartCsv(payload.rows, payload.title);
      setCsvComplete(true);
      clearPendingCheckoutCart();
    },
    [],
  );

  const applyCoupon = () => {
    if (!cart) return;
    const code = couponInput.trim();
    setCouponError(null);
    if (!code) {
      setCouponError("Enter a coupon code.");
      return;
    }
    if (isTestCheckoutCoupon(code)) {
      runTestCouponExport(cart);
      return;
    }
    setCouponError("Invalid coupon.");
  };

  const downloadAgain = () => {
    if (!cart) return;
    downloadBomCartCsv(cart.rows, cart.title);
  };

  if (!hydrated || !cart) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <section className="mx-auto w-full max-w-2xl px-6 pt-10 pb-6">
        <Link
          href="/app"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to agent
        </Link>
        <p className="mt-6 font-mono text-xs text-primary uppercase tracking-widest">Checkout</p>
        <h1 className="mt-2 font-display text-4xl text-gradient">Review your cart</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          BOMA fee settlement runs through{" "}
          <span className="text-foreground">AllScale</span>. Use coupon{" "}
          <span className="font-mono text-foreground">{TEST_CHECKOUT_COUPON}</span> in this demo to
          skip wallet checkout and download your priced BOM as CSV.
        </p>
      </section>

      <section className="mx-auto w-full max-w-2xl px-6 pb-16 space-y-6">
        <div className="rounded-2xl border border-border bg-card p-6 shadow-card">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-sm font-semibold">Order</h2>
              {cart.title && (
                <p className="mt-1 text-xs font-mono text-muted-foreground truncate max-w-md">
                  {cart.title}
                </p>
              )}
            </div>
            <div className="text-right">
              <p className="text-xs font-mono text-muted-foreground">Subtotal (parts)</p>
              <p className="font-mono text-xl tabular-nums">${cart.subtotal.toFixed(2)}</p>
            </div>
          </div>

          <ul className="mt-4 space-y-2 max-h-56 overflow-y-auto text-sm border-t border-border pt-4">
            {cart.rows.map((r, i) => (
              <li
                key={`${r.part}-${r.distributor}-${i}`}
                className="flex justify-between gap-3 font-mono text-xs"
              >
                <span className="text-foreground truncate">{r.part}</span>
                <span className="text-muted-foreground shrink-0">
                  ×{r.qty} · ${(r.qty * r.unit).toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-border bg-card p-6 shadow-card space-y-4">
          <h2 className="text-sm font-semibold">Coupon</h2>
          <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="checkout-coupon">Code</Label>
              <Input
                id="checkout-coupon"
                placeholder="Enter code"
                value={couponInput}
                onChange={(e) => setCouponInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") applyCoupon();
                }}
                disabled={csvComplete}
                autoComplete="off"
              />
            </div>
            <Button type="button" variant="hero" className="sm:shrink-0" onClick={applyCoupon} disabled={csvComplete}>
              Apply
            </Button>
          </div>
          {couponError && <p className="text-sm text-destructive">{couponError}</p>}
          {csvComplete && (
            <div className="rounded-xl border border-primary/40 bg-primary/5 px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex items-start gap-2 text-sm">
                <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" aria-hidden />
                <span>
                  AllScale checkout skipped. Your CSV export has started—check your downloads.
                </span>
              </div>
              <Button type="button" variant="glass" size="sm" className="gap-1.5 shrink-0" onClick={downloadAgain}>
                <Download className="h-4 w-4" />
                Download again
              </Button>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-dashed border-border bg-card/50 p-6">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
            AllScale payment
          </h2>
          <p className="mt-2 text-xs text-muted-foreground">
            Wallet-based checkout is not connected in this build. Use the coupon above to complete
            your export, or return to the agent to adjust your cart.
          </p>
          <Button type="button" variant="glass" className="mt-4 w-full sm:w-auto" disabled>
            Continue with AllScale
          </Button>
        </div>
      </section>

      <Footer />
    </div>
  );
}
