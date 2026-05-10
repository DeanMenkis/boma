import type { Metadata } from "next";
import { Instrument_Serif, Inter, JetBrains_Mono } from "next/font/google";

import { Providers } from "@/components/providers";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-stack-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-stack-mono",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-stack-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "BOMA — Bill Of Materials Agent",
    template: "%s — BOMA",
  },
  description:
    "Upload your parts list. BOMA finds every part on DigiKey and Mouser and builds a priced cart with shipping dates — automatically.",
  openGraph: {
    title: "BOMA — Bill Of Materials Agent",
    description:
      "Upload your parts list and get a priced cart from DigiKey, Mouser, and more — with shipping dates, in seconds.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} ${instrumentSerif.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
