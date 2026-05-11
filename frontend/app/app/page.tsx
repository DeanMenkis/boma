import type { Metadata } from "next";
import { Suspense } from "react";
import { BomAgentPage } from "@/screens/bom-agent-page";

export const metadata: Metadata = {
  title: "Agent",
  description: "Upload your parts list and let BOMA build a priced, ready-to-checkout cart.",
};

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-[40vh]" aria-hidden />}>
      <BomAgentPage />
    </Suspense>
  );
}
