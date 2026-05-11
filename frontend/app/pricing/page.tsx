import type { Metadata } from "next";
import { PricingPage } from "@/screens/pricing-page";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "BOMA pricing: $1 base plus $0.10 per BOM line. Pay in USDC via AllScale at checkout.",
  openGraph: {
    title: "Pricing — BOMA",
    description:
      "$1 + $0.10 per CSV line. Stablecoin checkout with AllScale; live pricing on DigiKey.",
  },
};

export default function Page() {
  return <PricingPage />;
}
