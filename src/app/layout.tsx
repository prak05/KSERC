import React from "react";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import GovBar from "@/components/premium/GovBar";
import Header from "@/components/premium/Header";
import Footer from "@/components/premium/Footer";
import { Toaster } from "@/components/ui/toaster";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "KSERC AI Truing-Up Premium v6",
  description: "Advanced AI-powered regulatory auditing and truing-up platform for KSERC.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased min-h-screen flex flex-col`}>
        <GovBar />
        <Header />
        <main className="flex-1">
          {children}
        </main>
        <Footer />
        <Toaster />
      </body>
    </html>
  );
}
