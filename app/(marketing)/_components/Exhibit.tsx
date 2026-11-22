import { Check, X } from "lucide-react"

import type { ExhibitCall, SiteConfig } from "@/lib/site/schema"
import { cn } from "@/lib/utils"

/**
 * One audited session, drawn the way an auditor leaves a page: every call on
 * its own line, a tick or a cross in the margin, a few words in pen beside the
 * lines that matter, and a stamp at the foot.
 *
 * It is the home page's argument. A reader who has never seen an agent's trace
 * learns from it what the product reads (the calls), what it produces (marks,
 * policy IDs, a severity), and that a violation usually spans several calls.
 *
 * Every word comes from `[home.exhibit]` of `data/site.toml`. The line numbers
 * are the calls' real order in the session, which is the one thing a reader
 * needs to follow the data from the read to the send.
 *
 * The entrance is one sequence: the lines are entered, then marked, then the
 * page is stamped. Each element only carries a delay; `globals.css` drops the
 * animations for a reader who asked for reduced motion.
 */
export default function Exhibit({
  exhibit,
  verdictLabel,
}: {
  exhibit: SiteConfig["home"]["exhibit"]
  /** `chat.verdict.riskyLabel`: the same words a verdict card in the chat uses. */
  verdictLabel: string
}) {
  const marksStart = 0.25 + exhibit.calls.length * 0.08
  const stampAt = marksStart + exhibit.calls.length * 0.07 + 0.15

  return (
    <figure className="w-full">
      <div className="rounded-lg border border-slate-300 bg-sheet shadow-[0_1px_0_#B9CBB9,0_18px_40px_-24px_rgba(19,36,28,0.45)]">
        {/* The page's heading: which session, whose, doing what. */}
        <header className="border-b border-slate-200 px-5 py-4 sm:px-6">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">
              {exhibit.label}
            </span>
            <span className="font-mono text-xs text-slate-700">{exhibit.sessionId}</span>
          </div>
          <p className="mt-2 text-sm text-primary">
            <span className="font-mono text-[13px] font-medium">{exhibit.agent}</span>
            <span className="mx-2 text-slate-400" aria-hidden="true">
              /
            </span>
            {exhibit.task}
          </p>
        </header>

        {/* The calls. The red line is a ledger's margin: marks go left of it. */}
        <ol className="relative py-2">
          <span
            aria-hidden="true"
            className="absolute bottom-0 left-12 top-0 w-px bg-accent/60 sm:left-14"
          />
          {exhibit.calls.map((call, index) => (
            <CallLine
              key={`${index}-${call.tool}`}
              call={call}
              number={index + 1}
              markLabel={call.mark === "flagged" ? exhibit.flaggedLabel : exhibit.cleanLabel}
              rowDelay={0.15 + index * 0.08}
              markDelay={marksStart + index * 0.07}
            />
          ))}
        </ol>

        {/* The finding. */}
        <footer className="flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-slate-200 px-5 py-4 sm:px-6">
          <span
            className="stamp animate-stamp-in -rotate-[5deg] border-accent text-accent"
            style={{ animationDelay: `${stampAt}s` }}
          >
            {verdictLabel}
            <span aria-hidden="true">/</span>
            {exhibit.severity}
          </span>
          <ul className="ml-auto flex flex-wrap gap-1.5">
            {exhibit.policies.map((policy) => (
              <li
                key={policy}
                className="rounded-sm border border-accent/40 bg-accent-wash px-1.5 py-0.5 font-mono text-xs text-accent"
              >
                {policy}
              </li>
            ))}
          </ul>
        </footer>
      </div>

      <figcaption className="mt-3 px-1 text-sm leading-relaxed text-slate-600">
        {exhibit.caption}
      </figcaption>
    </figure>
  )
}

function CallLine({
  call,
  number,
  markLabel,
  rowDelay,
  markDelay,
}: {
  call: ExhibitCall
  number: number
  /** What a screen reader says for the tick or the cross. */
  markLabel: string
  rowDelay: number
  markDelay: number
}) {
  const flagged = call.mark === "flagged"
  const Mark = flagged ? X : Check

  return (
    <li
      className={cn(
        "animate-row-in relative grid grid-cols-[3rem_1fr] sm:grid-cols-[3.5rem_1fr]",
        flagged && "bg-accent-wash/50",
      )}
      style={{ animationDelay: `${rowDelay}s` }}
    >
      <span className="flex justify-center pt-3">
        <Mark
          className={cn("animate-mark-in h-4 w-4", flagged ? "text-accent" : "text-tick")}
          strokeWidth={3}
          style={{ animationDelay: `${markDelay}s` }}
          role="img"
          aria-label={markLabel}
        />
      </span>

      <div className="py-2.5 pl-4 pr-5 sm:pr-6">
        <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
          <span className="font-mono text-[11px] tabular-nums text-slate-400">{number}</span>
          <span className="font-mono text-[13px] font-medium text-primary">{call.tool}</span>
          {call.status && (
            <span className="rounded-sm border border-slate-300 px-1 font-mono text-[10px] uppercase tracking-wider text-slate-600">
              {call.status}
            </span>
          )}
          {call.policies?.map((policy) => (
            <span key={policy} className="font-mono text-[11px] font-medium text-accent">
              {policy}
            </span>
          ))}
          {call.note && (
            <span
              className="animate-mark-in ml-auto -rotate-2 font-hand text-lg leading-none text-brand"
              style={{ animationDelay: `${markDelay + 0.1}s` }}
            >
              {call.note}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-[13px] leading-snug text-slate-600">{call.did}</p>
      </div>
    </li>
  )
}
