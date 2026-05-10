import Link from "next/link";
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  Upload,
  Sparkles,
  ShoppingCart,
  CircuitBoard,
  Cpu,
  Clock,
  Check,
} from "lucide-react";

export function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-60" />
        <div className="absolute inset-0 bg-hero" />
        <div className="relative mx-auto max-w-5xl px-6 pt-24 pb-32 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-border glass px-3 py-1 text-xs font-mono text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            v0.1 · DigiKey + Mouser live
          </div>

          <h1 className="mt-8 font-display text-5xl md:text-7xl leading-[1.05] text-gradient">
            BOM in.
            <br />
            Cart out.
          </h1>

          <p className="mx-auto mt-6 max-w-xl text-base text-muted-foreground">
            Upload your parts list. BOMA finds every part on DigiKey and Mouser, picks the best
            in-stock option, and gives you one priced cart with shipping dates.
          </p>

          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <Link href="/app">
              <Button variant="hero" size="xl">
                Upload your BOM <ArrowRight />
              </Button>
            </Link>
            <Link href="/pricing">
              <Button variant="glass" size="xl">
                See pricing
              </Button>
            </Link>
          </div>

        </div>
      </section>

      {/* Steps */}
      <section className="mx-auto max-w-7xl px-6 py-24">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: Upload,
              title: "Upload your list",
              body: "A spreadsheet with part names, quantities, and any notes.",
            },
            {
              icon: Sparkles,
              title: "Find every part",
              body: "We search DigiKey and Mouser at the same time and check what's in stock.",
            },
            {
              icon: ShoppingCart,
              title: "Get a cart",
              body: "One priced cart, with the price per part and a single shipping date.",
            },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-xl border border-border bg-card p-6 shadow-card">
              <div className="h-10 w-10 rounded-lg bg-surface-2 flex items-center justify-center text-primary">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mt-5 text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Built for */}
      <section className="mx-auto max-w-7xl px-6 py-24 border-t border-border">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <p className="font-mono text-xs text-primary uppercase tracking-widest">
              Built for hardware teams
            </p>
            <h2 className="mt-3 font-display text-4xl md:text-5xl text-gradient">
              Skip the tab juggling.
            </h2>
            <p className="mt-5 text-muted-foreground">
              Made for anyone tired of searching for parts one at a time and copying numbers
              between tabs.
            </p>
            <ul className="mt-6 space-y-3 text-sm font-mono">
              {[
                "Smart part matching, with backups if something's out of stock",
                "Live prices and stock for every line",
                "One shipping date for the whole cart",
                "Export to CSV, or send straight to DigiKey or Mouser",
              ].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary" /> {f}
                </li>
              ))}
            </ul>
          </div>

          <div className="relative rounded-2xl border border-border bg-card p-6 shadow-card">
            <div className="grid grid-cols-2 gap-4">
              {[
                { i: CircuitBoard, t: "Parts", v: "142 found" },
                { i: Cpu, t: "Sources", v: "DigiKey + Mouser" },
                { i: Clock, t: "Ships", v: "In 3 days" },
                { i: ShoppingCart, t: "Cart", v: "$1,204" },
              ].map(({ i: Icon, t, v }) => (
                <div key={t} className="rounded-lg border border-border bg-surface p-4">
                  <Icon className="h-5 w-5 text-primary" />
                  <div className="mt-3 font-mono text-xs text-muted-foreground">{t}</div>
                  <div className="mt-1 font-mono text-sm">{v}</div>
                </div>
              ))}
            </div>
            <div className="absolute -inset-px rounded-2xl pointer-events-none [mask-image:linear-gradient(180deg,black,transparent)]" />
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
