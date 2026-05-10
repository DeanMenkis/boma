import type { Metadata } from "next";
import { CheckoutPage } from "@/screens/checkout-page";

export const metadata: Metadata = {
  title: "Checkout",
  description: "Review your BOMA cart and complete checkout via AllScale or export CSV.",
};

export default function Page() {
  return <CheckoutPage />;
}
