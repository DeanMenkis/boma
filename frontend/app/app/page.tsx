import type { Metadata } from "next";
import { BomAgentPage } from "@/screens/bom-agent-page";

export const metadata: Metadata = {
  title: "Agent",
  description: "Upload your parts list and let BOMA build a priced, ready-to-checkout cart.",
};

export default function Page() {
  return <BomAgentPage />;
}
