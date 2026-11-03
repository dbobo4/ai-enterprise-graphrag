import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = { title: "Enterprise GraphRAG", description: "Course project" };

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <Link className="brand" href="/">Enterprise GraphRAG</Link>
          <nav><Link href="/">Chat</Link><Link href="/evaluate">Evaluate</Link></nav>
        </header>
        {children}
      </body>
    </html>
  );
}