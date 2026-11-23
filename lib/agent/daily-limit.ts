/**
 * The rules of the daily limit: how many questions the hosted page passes to
 * the agent in one day, all readers together. Pure: `tests_node/` runs it. The
 * counter that applies them is `daily-count.ts`.
 */

/** How many days the count of a past day stays in the table before it is removed. */
export const COUNT_KEPT_DAYS = 30

/**
 * The limit as it is configured: a whole number of questions, at least 1.
 * `null` for anything else, so a typo is a missing setting, never "no limit".
 */
export function parseDailyLimit(value: string | undefined): number | null {
  const text = (value ?? "").trim()
  return /^[1-9]\d*$/.test(text) ? Number(text) : null
}

/** The day a question counts for: the UTC date, such as `2026-01-31`. */
export function dayKey(now: Date): string {
  return now.toISOString().slice(0, 10)
}

/**
 * When the count of `now`'s day may be removed: Unix seconds,
 * `COUNT_KEPT_DAYS` after that day began.
 */
export function expiresAt(now: Date): number {
  const dayStart = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
  return dayStart / 1000 + COUNT_KEPT_DAYS * 86400
}
