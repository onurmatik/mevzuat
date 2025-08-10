import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/navbar";
import SearchNavbar from "@/components/search-navbar";
import { DocumentsChartProvider } from "@/components/documents-chart-context";
import { Suspense } from "react";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Mevzuat",
  description: "Your gateway to Turkish legislation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <DocumentsChartProvider>
          <Navbar />
          <Suspense fallback={null}>
            <SearchNavbar />
          </Suspense>
          <main>{children}</main>
        </DocumentsChartProvider>
      </body>
    </html>
  );
}
