import type { Metadata } from "next";
import { HomePage } from "@/screens/home-page";

export const metadata: Metadata = {
  title: "Source any parts list in seconds",
  description:
    "BOMA turns your parts list into a priced cart from DigiKey, Mouser, and more — with shipping dates included.",
};

export default function Page() {
  return <HomePage />;
}
