import { checkRateLimit } from "@vercel/firewall"
import { checkBotId } from "botid/server"

/**
 * Who may ask the agent a question. SERVER ONLY.
 *
 * Every question is a paid model call, and the hosted page is open to anyone.
 * Two checks stand between a request and the agent, both run by Vercel:
 *
 *   BotID        the browser solves an invisible challenge (see
 *                `instrumentation-client.ts`); a script that posts to the route
 *                without it is turned away.
 *   Rate limit   a rule of the Vercel Firewall, counted per client IP. The rule
 *                itself (how many requests in which window) lives in the
 *                project's Firewall settings on Vercel, not in this repo; this
 *                file only names it.
 *
 * Neither exists outside Vercel, so on a developer machine every caller is
 * allowed: the only caller there is the developer.
 *
 * Both limit one caller. What limits all callers together is the daily count
 * of `daily-count.ts`, which the route applies after these two.
 */

/**
 * The ID of the Firewall rule: a rule whose condition is `@vercel/firewall`
 * with this rate limit ID and whose action is "Rate Limit".
 */
export const CHAT_RATE_LIMIT_ID = "chat"

/** What the checks say about the caller of a request. */
export type CallerCheck = "allowed" | "bot" | "rateLimited"

/**
 * The Firewall has no rule named `CHAT_RATE_LIMIT_ID`: the deployment would
 * answer anyone as often as they ask.
 */
export class GuardNotConfiguredError extends Error {}

/**
 * Check the caller of `request`.
 *
 * @throws GuardNotConfiguredError when the rate limit rule does not exist. The
 *   route answers that with an error instead of calling the agent: a hosted
 *   page without its limit is a misconfiguration to notice, not to run with.
 * @throws whatever the two services throw when they cannot be reached.
 */
export async function checkCaller(request: Request): Promise<CallerCheck> {
  // Vercel sets VERCEL=1 at build time and at run time, nowhere else.
  if (process.env.VERCEL !== "1") return "allowed"

  const verification = await checkBotId()
  if (verification.isBot) return "bot"

  const { rateLimited, error } = await checkRateLimit(CHAT_RATE_LIMIT_ID, { request })
  if (error === "not-found") {
    throw new GuardNotConfiguredError(
      `The Vercel Firewall has no rate limit rule with the ID "${CHAT_RATE_LIMIT_ID}".`,
    )
  }
  return rateLimited ? "rateLimited" : "allowed"
}
