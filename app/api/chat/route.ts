import { randomUUID } from "node:crypto"

import { createUIMessageStream, createUIMessageStreamResponse } from "ai"

import { MAX_PROMPT_CHARS, lastUserText, toRuntimeSessionId } from "@/lib/agent/contract"
import { checkCaller } from "@/lib/agent/guard"
import { invokeAuditAgent } from "@/lib/agent/invoke"
import type { AuditUIMessage } from "@/lib/agent/message"
import { loadSite } from "@/lib/site/load"

/**
 * `POST /api/chat`: what the chat page's `useChat` posts to.
 *
 * It takes the last user message, asks the `AuditAgent` runtime (see
 * `lib/agent/invoke.ts`), and answers in the AI SDK's UI message stream. The
 * agent does not stream: it returns its whole answer after several model
 * calls, so the stream stays silent until then, and the page shows its
 * "thinking" state for that long.
 *
 * The browser sends the whole conversation with every request. Only the last
 * user message is used: the agent remembers the conversation itself, per
 * AgentCore runtime session, and the chat's ID selects that session.
 *
 * Every question is a paid model call, so the caller is checked first (see
 * `lib/agent/guard.ts`): a script, or a reader who asked too often, is turned
 * away before anything else is looked at.
 */

/** An audit can take a minute; the platform default would cut a slow one off. */
export const maxDuration = 300

export async function POST(request: Request): Promise<Response> {
  const site = loadSite()

  try {
    const caller = await checkCaller(request)
    if (caller === "bot") {
      return new Response(site.chat.messages.botBlocked, { status: 403 })
    }
    if (caller === "rateLimited") {
      return new Response(site.chat.messages.rateLimited, { status: 429 })
    }
  } catch (error) {
    // The check itself failed, or the rate limit rule is missing. Nobody is
    // answered without the check: the agent is not called.
    console.error("[api/chat] the caller could not be checked:", error)
    return new Response(site.chat.messages.agentUnavailable, { status: 503 })
  }

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return new Response("The request body is not JSON.", { status: 400 })
  }
  const { id, messages } = (body ?? {}) as { id?: unknown; messages?: unknown }

  const prompt = lastUserText(messages)
  if (!prompt) {
    return new Response("The request has no user message.", { status: 400 })
  }
  if (prompt.length > MAX_PROMPT_CHARS) {
    return new Response(site.chat.messages.promptTooLong, { status: 400 })
  }
  const runtimeSessionId = toRuntimeSessionId(id, randomUUID)

  const stream = createUIMessageStream<AuditUIMessage>({
    execute: async ({ writer }) => {
      const answer = await invokeAuditAgent(prompt, runtimeSessionId)

      if (answer.refused) {
        writer.write({ type: "data-refusal", data: { message: answer.result } })
        return
      }
      // The verdicts first: the conclusion, then the evidence in prose.
      for (const verdict of answer.verdicts) {
        writer.write({ type: "data-verdict", id: verdict.session_id, data: verdict })
      }
      writer.write({ type: "text-start", id: "answer" })
      writer.write({ type: "text-delta", id: "answer", delta: answer.result })
      writer.write({ type: "text-end", id: "answer" })
    },
    // What went wrong is for the server's log; the reader gets one sentence
    // that does not name an ARN, a credential, or a stack trace.
    onError: (error) => {
      console.error("[api/chat] the agent call failed:", error)
      return site.chat.messages.agentUnavailable
    },
  })
  return createUIMessageStreamResponse({ stream })
}
