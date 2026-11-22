import type React from "react"
import type { Metadata, Viewport } from "next"
import { Bricolage_Grotesque, Caveat, IBM_Plex_Mono, Public_Sans } from "next/font/google"
import { generateSEOMetadata } from "@/lib/seo/generateMetadata"
import { loadSite } from "@/lib/site/load"
import "./globals.css"

// Four voices; `tailwind.config.ts` says what each is for.
const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-display" })
const body = Public_Sans({ subsets: ["latin"], variable: "--font-body" })
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600"],
})
const hand = Caveat({ subsets: ["latin"], variable: "--font-hand", weight: ["500", "600"] })

const { seo } = loadSite()

export const metadata: Metadata = {
  ...generateSEOMetadata({
    title: seo.title,
    description: seo.description,
  }),
  icons: {
    icon: [
      { url: '/icon.png', type: 'image/png' },
    ],
    shortcut: '/icon.png',
    apple: '/icon.png',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${body.variable} ${mono.variable} ${hand.variable}`}
    >
      <body className={`${body.className} antialiased`}>{children}</body>
    </html>
  )
}
