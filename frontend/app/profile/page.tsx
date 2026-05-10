import type { Metadata } from "next";

import { ProfilePage } from "@/screens/profile-page";

export const metadata: Metadata = {
  title: "Profile",
  description: "Your account and locally saved BOMs.",
};

export default function Page() {
  return <ProfilePage />;
}
