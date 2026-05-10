import type { Metadata } from "next";
import { AuthCard } from "@/components/site/AuthCard";

export const metadata: Metadata = {
  title: "Log in",
  description: "Log in to your BOMA account.",
};

export default function Page() {
  return <AuthCard mode="login" />;
}
