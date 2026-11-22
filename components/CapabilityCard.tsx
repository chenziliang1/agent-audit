"use client"

import ConceptTooltip from "@/components/ConceptTooltip"
import { getIcon } from "@/lib/icons"
import type { Capability } from "@/lib/site/schema"

/**
 * One of the four things the audit looks for, as a cell with an explanation
 * behind it.
 *
 * The home page and the agent's welcome screen both show these four, at
 * different sizes. One component rather than two so they cannot drift: an
 * earlier arrangement had two separate arrays for the two screens, and they
 * had already drifted into naming the same four things differently.
 *
 * `title` is a concept name and is therefore unreadable to anyone outside the
 * domain. `subtitle` is the one-line translation; the tooltip is the paragraph
 * behind it, on hover, focus, or tap.
 *
 * The cell draws no frame of its own: on the home page the four share one
 * ruled band, on the welcome screen a grid of sheets. The caller passes the
 * edges through `className`.
 */
export default function CapabilityCard({
  capability,
  align = "start",
  compact = false,
  className = "",
}: {
  capability: Capability
  /** Which edge the tooltip hangs from while the grid is two columns wide. */
  align?: "start" | "end"
  /** The agent's welcome screen has less room than the home page. */
  compact?: boolean
  className?: string
}) {
  const Icon = getIcon(capability.icon)

  return (
    <ConceptTooltip
      text={capability.tooltip}
      align={align}
      className={`group cursor-help transition-colors hover:bg-sheet focus-visible:bg-sheet ${
        compact ? "p-4" : "px-5 py-6"
      } ${className}`}
    >
      <div className="flex items-center gap-2.5">
        <Icon className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
        <p
          className={`font-display font-semibold tracking-tight text-primary ${
            compact ? "text-sm" : "text-base"
          }`}
        >
          {capability.title}
        </p>
      </div>
      <p className={`mt-2 leading-snug text-slate-600 ${compact ? "text-xs" : "text-sm"}`}>
        {capability.subtitle}
      </p>
      {/* The dashed rule is the only thing telling a reader there is something
          to hover over. Without it the hint is invisible. */}
      <span
        aria-hidden="true"
        className="mt-3 block w-8 border-b border-dashed border-slate-400 transition-colors group-hover:border-brand"
      />
    </ConceptTooltip>
  )
}
