"use client"

import { humanizeCategory } from "@/lib/agent/contract"
import type { SessionVerdict, Severity } from "@/lib/agent/contract"
import type { SiteConfig } from "@/lib/site/schema"
import { cn } from "@/lib/utils"

type VerdictLabels = SiteConfig["chat"]["verdict"]

/**
 * How many of the four boxes a severity fills. The scale is ordered, so it is
 * drawn as a length rather than as four unrelated colours: `high` is visibly
 * one short of `critical` without a reader having to learn a palette.
 */
const SEVERITY_LEVEL: Record<Severity, number> = {
  none: 0,
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
}

const SEVERITY_STEPS = [1, 2, 3, 4]

/**
 * The agent's verdict on one session, as data rather than prose: whether it
 * broke a policy, how badly, which policies, and which calls.
 *
 * It is drawn from the structured verdict the agent recorded, not parsed out
 * of its text, so what the card says and what an evaluation reads are the same
 * values.
 *
 * It looks like the foot of the audited page on the home page: the finding is
 * stamped, in red for a violation and in green for a clean session, and the
 * IDs are set in the face every ID on the site is set in.
 *
 * `models` are the models that wrote the answer this verdict belongs to: the
 * configured model declines some sessions that quote attacks, and a fallback
 * model then judges them. Empty when the runtime did not say.
 */
export function VerdictCard({
  verdict,
  models = [],
  labels,
}: {
  verdict: SessionVerdict
  models?: string[]
  labels: VerdictLabels
}) {
  const level = SEVERITY_LEVEL[verdict.severity]

  return (
    <div
      className={cn(
        "rounded-md border border-slate-300 border-l-2 bg-surface px-4 py-3.5",
        verdict.risky ? "border-l-accent" : "border-l-tick",
      )}
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span
          className={cn(
            "stamp -rotate-2",
            verdict.risky ? "border-accent text-accent" : "border-tick text-tick",
          )}
        >
          {verdict.risky ? labels.riskyLabel : labels.cleanLabel}
        </span>

        {level > 0 && (
          <span className="flex items-center gap-2">
            <span className="flex gap-0.5" aria-hidden="true">
              {SEVERITY_STEPS.map((step) => (
                <span
                  key={step}
                  className={cn(
                    "h-3 w-2 rounded-[1px] border border-accent",
                    step <= level && "bg-accent",
                  )}
                />
              ))}
            </span>
            <span className="font-mono text-xs font-medium uppercase tracking-wider text-primary">
              {humanizeCategory(verdict.severity)}
            </span>
          </span>
        )}

        <span className="ml-auto font-mono text-xs text-slate-600">
          <span className="sr-only">{labels.sessionLabel} </span>
          {verdict.session_id}
        </span>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-slate-700">{verdict.rationale}</p>

      {(verdict.risky || models.length > 0) && (
        <dl className="mt-3 flex flex-col gap-2 border-t border-slate-200 pt-3">
          {verdict.risky && (
            <>
              <ChipRow label={labels.policiesLabel} items={verdict.policy_ids} mono flagged />
              <ChipRow label={labels.categoriesLabel} items={verdict.categories.map(humanizeCategory)} />
              <ChipRow label={labels.flaggedCallsLabel} items={verdict.flagged_call_ids} mono />
            </>
          )}
          <ChipRow label={labels.judgedByLabel} items={models} mono />
        </dl>
      )}
    </div>
  )
}

function ChipRow({
  label,
  items,
  mono = false,
  flagged = false,
}: {
  label: string
  items: string[]
  mono?: boolean
  /** Policy IDs are set in red, as they are beside a flagged call on the home page. */
  flagged?: boolean
}) {
  if (items.length === 0) return null
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:gap-3">
      <dt className="w-28 shrink-0 font-mono text-[11px] uppercase tracking-wider text-slate-500">
        {label}
      </dt>
      <dd className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span
            key={item}
            className={cn(
              "rounded-sm border px-1.5 py-0.5 text-xs",
              mono && "font-mono",
              flagged
                ? "border-accent/40 bg-accent-wash text-accent"
                : "border-slate-300 bg-sheet text-primary",
            )}
          >
            {item}
          </span>
        ))}
      </dd>
    </div>
  )
}

/**
 * Shown in place of an answer when the model declined to give one. Styled
 * apart from both an answer and a verdict: it is neither a finding nor a
 * clean result, and must not be mistaken for either. The dashed frame in pen
 * blue is the auditor's own note, not a stamp.
 */
export function RefusalNotice({ message, labels }: { message: string; labels: VerdictLabels }) {
  return (
    <div className="rounded-md border border-dashed border-brand bg-brand-wash px-4 py-3.5">
      <p className="font-mono text-xs font-semibold uppercase tracking-wider text-brand-dark">
        {labels.refusalTitle}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-slate-700">{message}</p>
    </div>
  )
}
