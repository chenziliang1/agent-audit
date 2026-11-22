"use client"

import { useState } from "react"
import Link from "next/link"
import { ArrowRight, BookOpen } from "lucide-react"

import BusinessContextModal from "@/components/BusinessContextModal"
import CapabilityCard from "@/components/CapabilityCard"
import type { SiteConfig } from "@/lib/site/schema"

import Exhibit from "./Exhibit"

/**
 * The home page: what the product is on the left, one audit on the right, and
 * under both the four things it looks for.
 *
 * The audit is the argument, so it sits beside the headline rather than below
 * the fold: a reader sees what the agent returns before reading a word about
 * it. On a narrow screen it follows the call to action.
 */
export default function Hero({
  site,
  businessContext,
}: {
  site: SiteConfig
  /** Raw Markdown of `data/business-context.md`, read on the server. */
  businessContext: string
}) {
  const [contextOpen, setContextOpen] = useState(false)

  const { home, capabilities, chat } = site

  return (
    <section className="ledger-rules px-4 pb-16 pt-28 sm:px-6 lg:px-8 lg:pt-32">
      <div className="mx-auto w-full max-w-6xl">
        <div className="grid items-start gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:gap-14">
          {/* What it is, and the way in. */}
          <div>
            <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-slate-600">
              {home.tagline}
            </p>

            <h1 className="mt-4 font-display text-6xl font-bold leading-[0.95] tracking-[-0.03em] text-primary sm:text-7xl lg:text-[5.25rem]">
              {home.headline.prefix}
              <span className="relative whitespace-nowrap">
                {home.headline.accent}
                {/* The auditor's underline: one pass of the red pen. */}
                <span
                  aria-hidden="true"
                  className="absolute -bottom-1 left-0 h-[0.09em] w-full -rotate-1 rounded-full bg-accent"
                />
              </span>
            </h1>

            <p className="mt-8 max-w-xl text-lg leading-relaxed text-slate-700">
              {home.description}
            </p>

            <div className="mt-9 flex flex-col items-start gap-4">
              <Link
                href="/chat"
                className="group inline-flex items-center gap-3 rounded-md bg-primary px-6 py-3.5 text-base font-semibold text-primary-foreground transition-colors hover:bg-brand"
              >
                {home.cta.title}
                <ArrowRight
                  className="h-5 w-5 transition-transform group-hover:translate-x-1"
                  aria-hidden="true"
                />
              </Link>
              <p className="text-sm text-slate-600">{home.cta.subtitle}</p>

              {/* One paragraph cannot carry a whole business domain; this opens
                  the two or three screens that can. */}
              <button
                type="button"
                onClick={() => setContextOpen(true)}
                className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-brand underline decoration-brand-soft underline-offset-4 transition-colors hover:text-brand-dark hover:decoration-brand"
              >
                <BookOpen className="h-4 w-4" aria-hidden="true" />
                {home.businessContext.triggerLabel}
              </button>
            </div>
          </div>

          {/* One audit, as the agent returned it. */}
          <Exhibit exhibit={home.exhibit} verdictLabel={chat.verdict.riskyLabel} />
        </div>

        {/* The four things it looks for. Same four on the agent's welcome
            screen, from the same `[[capabilities]]`. */}
        <div className="mt-16 grid gap-px border-y border-slate-300 bg-slate-300 sm:grid-cols-2 lg:grid-cols-4">
          {capabilities.map((cap, index) => (
            <CapabilityCard
              key={cap.title}
              capability={cap}
              // Two columns on a tablet: outer cells hang the bubble from
              // their outer edge so it cannot run off screen.
              align={index % 2 === 0 ? "start" : "end"}
              // The band's rules are the grid's gaps showing through.
              className="bg-paper"
            />
          ))}
        </div>

        {/* What was audited, and what it is built with. */}
        <div className="mt-6 flex flex-col gap-3 lg:flex-row lg:items-baseline lg:justify-between">
          <p className="text-sm text-slate-600">{home.blurb}</p>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-slate-500">
            {home.techStack.map((tech) => (
              <li key={tech}>{tech}</li>
            ))}
          </ul>
        </div>
      </div>

      <BusinessContextModal
        open={contextOpen}
        onClose={() => setContextOpen(false)}
        labels={home.businessContext}
        markdown={businessContext}
      />
    </section>
  )
}
