import type { UIMessage } from "ai"

import type { SessionVerdict } from "./contract"

/**
 * A chat message of this app: the AI SDK's `UIMessage`, plus the two data
 * parts the route adds to an assistant message.
 *
 *   data-verdict   one per session the agent audited for the answer, with the
 *                  models that wrote that answer. The page draws it as a card;
 *                  nobody parses the prose for a conclusion.
 *   data-refusal   the model declined to answer. It replaces the text part, so
 *                  a refusal can never be read as an ordinary answer.
 */
export type AuditUIMessage = UIMessage<
  never,
  {
    verdict: SessionVerdict & { models: string[] }
    refusal: { message: string }
  }
>
