import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navigation from "@/components/Navigation";

const inter = Inter({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "Publicus | Selling to government, simplified.",
  description: "No more procurement pain. Publicus helps contractors find, qualify, and respond to more government opportunities using AI.",
  icons: {
    icon: "https://d41ru60qohkrm.cloudfront.net/PublicusLogo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable}`}>
      <body className="bg-white text-black font-body">
        <Navigation />
        {children}
      </body>
    </html>
  );
}
