import type { Metadata } from "next";
import { EB_Garamond, Source_Code_Pro } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const ebGaramond = EB_Garamond({
  subsets: ["latin"],
  variable: "--font-eb-garamond",
  weight: ["400", "600", "700"],
});

const sourceCodePro = Source_Code_Pro({
  subsets: ["latin"],
  variable: "--font-source-code-pro",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "KSERC AI Truing-Up Tool",
  description: "AI-based tracking and truing-up of accounts for distribution licensees. Work Order KSERC/CSO/03-05.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`font-sans antialiased ${ebGaramond.variable} ${sourceCodePro.variable}`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
