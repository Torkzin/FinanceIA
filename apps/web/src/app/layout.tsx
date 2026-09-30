import type { Metadata } from "next";
import { AuthProvider } from "@/components/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinanceAI — Financial operations, made intelligent",
  description: "Responsible AI for business financial operations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body><AuthProvider>{children}</AuthProvider></body>
    </html>
  );
}

