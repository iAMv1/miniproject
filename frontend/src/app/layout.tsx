import type { Metadata } from "next";
import { ClientProviders } from "./client-providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "MindPulse — Behavioral Awareness",
  description: "Privacy-first behavioral awareness with explicit signal-quality context and user-controlled data.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-bg text-gray-200" suppressHydrationWarning>
        <ClientProviders>
          {children}
          <div className="noise-overlay" />
        </ClientProviders>
      </body>
    </html>
  );
}
