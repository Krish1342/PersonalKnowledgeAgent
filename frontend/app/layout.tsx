import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Navigation } from "@/components/Navigation";

export const metadata: Metadata = {
  title: "Second Brain | Personal Knowledge Base",
  description: "RAG-powered personal knowledge base with LangGraph agents",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950">
        <Providers>
          <Navigation />
          <main className="pt-16">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
