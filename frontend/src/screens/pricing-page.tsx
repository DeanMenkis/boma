import Link from "next/link";
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { PricingFeeEstimator } from "@/components/site/PricingFeeEstimator";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { BOMA_BASE_FEE_USD, BOMA_PER_LINE_USD } from "@/lib/pricing";

const ALLSCALE_DOCS = "https://docs.allscale.io";

const features = [
  "Live distributor pricing and stock on every line",
  "DigiKey live pricing in one flow. Export CSV or open a prefilled cart.",
  "Checkout in USDC via AllScale",
];

export function PricingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <section className="relative">
        <div className="absolute inset-0 bg-hero opacity-60" />
        <div className="relative mx-auto max-w-3xl px-6 pt-20 pb-12 text-center">
          <p className="font-mono text-xs text-primary uppercase tracking-widest">Pricing</p>
          <h1 className="mt-3 font-display text-5xl md:text-6xl text-gradient">
            One simple fee per BOM.
          </h1>
          <p className="mt-5 text-muted-foreground">
            Pay BOMA in USDC through{" "}
            <a
              href={ALLSCALE_DOCS}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-4 hover:text-primary/90"
            >
              AllScale
            </a>
            .
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-24">
        <div className="mx-auto grid max-w-4xl gap-10 lg:grid-cols-2 lg:items-start">
          <PricingFeeEstimator />

          <div className="relative rounded-2xl border border-primary/40 bg-card p-8 shadow-card shadow-glow flex flex-col">
            <span className="inline-flex w-fit rounded-full bg-primary/15 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-primary">
              AllScale checkout
            </span>
            <h2 className="mt-4 font-display text-3xl text-gradient">Usage-based</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Priced from your uploaded CSV. Each BOM row counts as one line.
            </p>

            <div className="mt-8 flex items-baseline gap-2 flex-wrap">
              <span className="font-display text-5xl tabular-nums">
                ${BOMA_BASE_FEE_USD.toFixed(0)}
              </span>
              <span className="text-muted-foreground text-sm">base</span>
              <span className="text-muted-foreground/80">+</span>
              <span className="font-display text-5xl tabular-nums">
                ${BOMA_PER_LINE_USD.toFixed(2)}
              </span>
              <span className="text-muted-foreground text-sm">/ line</span>
            </div>

            <ul className="mt-8 space-y-2.5 text-sm flex-1">
              {features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <Check className="h-4 w-4 mt-0.5 text-primary shrink-0" /> {f}
                </li>
              ))}
            </ul>

            <Link href="/app" className="mt-10 block">
              <Button variant="hero" size="lg" className="w-full">
                Upload a BOM
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
