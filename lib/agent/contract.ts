/**
 * The contract between the chat page and the `AuditAgent` runtime, as plain
 * functions: what the route takes from a chat request, and what it accepts as
 * the agent's answer.
 *
 * No import of Next.js, the AWS SDK, or the AI SDK, and only syntax Node can
 * strip, so `tests_node/` runs this file as it is.
 *
 * The answer's shape is `AuditAgentResponse` of `agent_app/audit/audit_agent.py`.
 * The two are kept in step by hand: a field added there is added here, and
 * `parseAgentResponse` rejects an answer that lacks a field this file names.
 */

/** How bad a session is; `none` is the severity of a session that is not risky. */
export type Severity = "none" | "low" | "medium" | "high" | "critical"

const SEVERITIES: readonly string[] = ["none", "low", "medium", "high", "critical"]

/** The agent's conclusion on one session it audited. */
export interface SessionVerdict {
  session_id: string
  risky: boolean
  severity: Severity
  categories: string[]
  policy_ids: string[]
  flagged_call_ids: string[]
  rationale: string
}

/** What the agent answers. */
export interface AuditAgentResponse {
  /** The answer as Markdown; a fixed explanation when `refused`. */
  result: string
  /** One verdict per session audited for this answer; empty when refused. */
  verdicts: SessionVerdict[]
  /** The model declined to answer: nothing was audited. */
  refused: boolean
  /**
   * The Claude models that wrote the answer, in the order first used. More
   * than one when a model call was answered by a fallback model; empty from a
   * runtime that does not say.
   */
  models: string[]
}

/** The agent answered with something that is not an `AuditAgentResponse`. */
export class AgentResponseError extends Error {}

/**
 * The longest question the route passes on. An audit question is a sentence or
 * two; anything far longer is a paste, and every character of it is paid for.
 */
export const MAX_PROMPT_CHARS = 4000

/**
 * AgentCore Runtime accepts a session ID of 33 to 256 characters. A chat ID of
 * the AI SDK has 16, so the prefix alone brings it to 33.
 */
const SESSION_ID_PREFIX = "agent-audit-chat-"
const SESSION_ID_MIN_CHARS = 33
const SESSION_ID_MAX_CHARS = 256

/**
 * The text of the last user message of a `useChat` request body's `messages`,
 * trimmed; empty when there is none.
 *
 * Only the last one: the agent keeps the conversation itself, per runtime
 * session, so the history the browser sends along is not replayed to it.
 */
export function lastUserText(messages: unknown): string {
  if (!Array.isArray(messages)) return ""
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (!isRecord(message) || message.role !== "user") continue
    if (!Array.isArray(message.parts)) return ""
    return message.parts
      .filter((part) => isRecord(part) && part.type === "text")
      .map((part) => (typeof part.text === "string" ? part.text : ""))
      .join("\n")
      .trim()
  }
  return ""
}

/**
 * The AgentCore runtime session ID of a chat: the same chat always maps to the
 * same session, which is what makes a follow-up question reach the agent that
 * answered the first one.
 *
 * The chat ID comes from the browser, so it is not trusted to be well formed:
 * anything outside letters, digits, `-` and `_` is dropped, and the result is
 * padded or cut to the length AgentCore accepts. A request without a usable
 * chat ID gets `random()`, so it starts a conversation of its own.
 */
export function toRuntimeSessionId(chatId: unknown, random: () => string): string {
  const cleaned = typeof chatId === "string" ? chatId.replace(/[^A-Za-z0-9_-]/g, "") : ""
  const id = SESSION_ID_PREFIX + (cleaned || random().replace(/[^A-Za-z0-9_-]/g, ""))
  return id.padEnd(SESSION_ID_MIN_CHARS, "0").slice(0, SESSION_ID_MAX_CHARS)
}

/**
 * `raw`, the parsed JSON of the agent's answer, as an `AuditAgentResponse`.
 *
 * Checked field by field rather than cast: the page renders these values, and
 * an answer of another shape (an error body, an older runtime) must fail here
 * with the field's name, not as `undefined` inside a component.
 *
 * `refused` and `models` may be missing: a runtime deployed before either
 * field existed does not send it. Such a runtime never refused, and which
 * model answered is then not known.
 */
export function parseAgentResponse(raw: unknown): AuditAgentResponse {
  if (!isRecord(raw)) throw new AgentResponseError("the answer is not an object")
  if (typeof raw.result !== "string") throw new AgentResponseError("result is not a string")
  if (!Array.isArray(raw.verdicts)) throw new AgentResponseError("verdicts is not a list")
  if (raw.refused !== undefined && typeof raw.refused !== "boolean") {
    throw new AgentResponseError("refused is not a boolean")
  }
  return {
    result: raw.result,
    verdicts: raw.verdicts.map(parseVerdict),
    refused: raw.refused === true,
    models: raw.models === undefined ? [] : stringList(raw.models, "models"),
  }
}

function parseVerdict(raw: unknown, index: number): SessionVerdict {
  const where = `verdicts[${index}]`
  if (!isRecord(raw)) throw new AgentResponseError(`${where} is not an object`)
  if (typeof raw.session_id !== "string") throw new AgentResponseError(`${where}.session_id is not a string`)
  if (typeof raw.risky !== "boolean") throw new AgentResponseError(`${where}.risky is not a boolean`)
  if (typeof raw.severity !== "string" || !SEVERITIES.includes(raw.severity)) {
    throw new AgentResponseError(`${where}.severity is not a severity`)
  }
  if (typeof raw.rationale !== "string") throw new AgentResponseError(`${where}.rationale is not a string`)
  return {
    session_id: raw.session_id,
    risky: raw.risky,
    severity: raw.severity as Severity,
    categories: stringList(raw.categories, `${where}.categories`),
    policy_ids: stringList(raw.policy_ids, `${where}.policy_ids`),
    flagged_call_ids: stringList(raw.flagged_call_ids, `${where}.flagged_call_ids`),
    rationale: raw.rationale,
  }
}

function stringList(raw: unknown, where: string): string[] {
  if (!Array.isArray(raw) || raw.some((item) => typeof item !== "string")) {
    throw new AgentResponseError(`${where} is not a list of strings`)
  }
  return raw as string[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

/** Words of a category that are acronyms, and so keep their capitals. */
const ACRONYMS: readonly string[] = ["pii", "ssrf", "iam"]

/**
 * A policy category as the policy document spells it, for a reader:
 * `PROMPT_INJECTION_COMPLIANCE` becomes `Prompt injection compliance`, and
 * `PII_OVERREACH` becomes `PII overreach`.
 */
export function humanizeCategory(category: string): string {
  const words = category
    .toLowerCase()
    .split("_")
    .filter((word) => word !== "")
    .map((word) => (ACRONYMS.includes(word) ? word.toUpperCase() : word))
    .join(" ")
  return words.charAt(0).toUpperCase() + words.slice(1)
}
