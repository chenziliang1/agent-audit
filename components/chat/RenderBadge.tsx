import { ShieldCheck, Table2, Workflow } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import type { RenderKind } from "@/lib/site/schema"

/**
 * The glyph on a kickstart button saying what pressing it will draw.
 *
 * Twelve buttons all look alike, and three of them produce a verdict card,
 * three a table, and three a flowchart. Without a mark, the only way to find
 * out which is to press one and wait for a model to answer. The glyph turns the
 * quota that `lib/site/kickstarts.ts` enforces into something a reader can see.
 *
 * Not authored copy: the mapping lives here rather than as an emoji inside the
 * question text, so a question stays a sentence and the mark stays presentation.
 * `render = "free"` deliberately draws nothing -- a badge on every button marks
 * nothing at all.
 *
 * These three icons are imported directly rather than through `lib/icons.ts`.
 * That map is the set `site.toml` may name; this mapping is fixed by the
 * renderer and is not the copy's to choose.
 */
const BADGES: Record<Exclude<RenderKind, "free">, { Icon: LucideIcon; label: string }> = {
  verdict: { Icon: ShieldCheck, label: "Answers with a verdict on a session" },
  table: { Icon: Table2, label: "Answers with a table" },
  flowchart: { Icon: Workflow, label: "Answers with a flowchart" },
}

export function RenderBadge({ render }: { render: RenderKind }) {
  if (render === "free") return null

  const { Icon, label } = BADGES[render]
  return (
    <Icon
      className="w-3.5 h-3.5 shrink-0 text-slate-500 group-hover:text-accent transition-colors"
      role="img"
      aria-label={label}
    />
  )
}
