import { initBotId } from "botid/client/core"

/**
 * Runs once in the browser, before the app. It makes the browser attach the
 * answer of Vercel BotID's invisible challenge to every question the chat page
 * posts; `checkCaller` of `lib/agent/guard.ts` reads it on the server. A route
 * that is checked there and not listed here fails its check for everyone.
 */
initBotId({
  protect: [{ path: "/api/chat", method: "POST" }],
})
