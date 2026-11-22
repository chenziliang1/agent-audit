"use client"

import Hero from "./_components/Hero"
import type { SiteConfig } from "@/lib/site/schema"

export default function HomePageContent({
  site,
  businessContext,
}: {
  site: SiteConfig
  businessContext: string
}) {
  return (
    <div className="flex min-h-screen flex-col bg-paper font-body text-primary">
      <div className="flex-1">
        <Hero site={site} businessContext={businessContext} />
      </div>

      <footer className="border-t border-slate-300 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <p className="font-mono text-xs text-slate-500">
            &copy; {new Date().getFullYear()} {site.brand.footerName}. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}
