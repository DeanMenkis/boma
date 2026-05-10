import type { Metadata } from "next";
import { AuthCard } from "@/components/site/AuthCard";

export const metadata: Metadata = {
  title: "Sign up",
  description: "Create a free BOMA account and source your first parts list in seconds.",
};

export default function Page() {
  return <AuthCard mode="signup" />;
}
