import Link from "next/link";
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";

const plans = [
  {
    name: "Hobby",
    price: "$0",
    period: "/forever",
    blurb: "For tinkerers and weekend builds.",
    cta: "Start free",
    href: "/signup",
    features: ["3 lists / month", "Up to 50 parts per list", "DigiKey + Mouser", "Export to CSV"],
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    blurb: "For people shipping real hardware.",
    cta: "Go Pro",
    href: "/signup",
    featured: true,
    features: [
      "Unlimited lists",
      "Up to 1,000 parts per list",
      "Priority queue",
      "Saved projects and history",
      "One-click cart hand-off",
    ],
  },
  {
    name: "Team",
    price: "Custom",
    period: "",
    blurb: "For hardware companies and labs.",
    cta: "Contact sales",
    href: "/signup",
    features: [
      "Single sign-on (SSO) and roles",
      "Approval workflows",
      "Custom suppliers",
      "API access",
      "Dedicated support",
    ],
  },
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
            Pay for what you build.
          </h1>
          <p className="mt-5 text-muted-foreground">
            Free to try on small lists. Upgrade when you need more.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-24 grid md:grid-cols-3 gap-6">
        {plans.map((p) => (
          <div
            key={p.name}
            className={`relative rounded-2xl border p-8 shadow-card flex flex-col ${
              p.featured ? "border-primary/40 bg-card shadow-glow" : "border-border bg-card"
            }`}
          >
            {p.featured && (
              <span className="absolute -top-3 left-8 px-2 py-0.5 rounded-full bg-primary text-primary-foreground text-[10px] font-mono uppercase tracking-wider">
                Most popular
              </span>
            )}
            <h3 className="font-mono text-sm text-muted-foreground">{p.name}</h3>
            <div className="mt-3 flex items-baseline gap-1">
              <span className="font-display text-5xl">{p.price}</span>
              <span className="text-muted-foreground text-sm">{p.period}</span>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">{p.blurb}</p>

            <ul className="mt-6 space-y-2.5 text-sm flex-1">
              {p.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <Check className="h-4 w-4 mt-0.5 text-primary shrink-0" /> {f}
                </li>
              ))}
            </ul>

            <Link href={p.href} className="mt-8 block">
              <Button variant={p.featured ? "hero" : "glass"} size="lg" className="w-full">
                {p.cta}
              </Button>
            </Link>
          </div>
        ))}
      </section>

      <Footer />
    </div>
  );
}
