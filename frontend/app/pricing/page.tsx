import type { Metadata } from "next";
import { PricingPage } from "@/screens/pricing-page";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Simple, usage-based pricing for teams sourcing parts. Free to start.",
  openGraph: {
    title: "Pricing — BOMA",
    description:
      "Free to start. Pro and Team plans for hardware shops sourcing parts on DigiKey, Mouser, and more.",
  },
};

export default function Page() {
  return <PricingPage />;
}
