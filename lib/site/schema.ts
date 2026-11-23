import type { IconName } from "@/lib/icons"

/**
 * The shape of `data/site.toml`, as TypeScript sees it.
 *
 * This file used to be `config/site.ts`: a TypeScript literal, which the
 * compiler checked for free. TOML gives that up on purpose, so that everything
 * written for a reader sits in one directory, and so that the copy can carry real comments next to the sentence
 * they explain. What the compiler used to catch is now caught by `load.ts` at
 * startup: `REQUIRED_SITE_KEYS` for missing keys, `assertIconsExist` for icon
 * names. Both throw rather than render a blank.
 *
 * `icon` is still typed against the names `lib/icons.ts` exports, which is what
 * makes a component's use of an icon name safe. The value arriving from TOML is
 * what needs the runtime check.
 */

/**
 * One of this app's four business lines.
 *
 * Rendered twice, as a card on the home page and again on the agent's welcome
 * screen, from this one entry. It used to be two arrays -- `home.capabilities`
 * and `chat.insights` -- naming the same four things in two vocabularies, and
 * they had already drifted: the second thread was "Portfolio Concentration" on
 * one screen and "Portfolio Health" on the other, with a different icon and no
 * tooltip at all.
 */
export interface Capability {
  icon: IconName
  /** The concept name. Precise to an insider, opaque to everyone else. */
  title: string
  /** One plain line saying what the concept buys you. */
  subtitle: string
  /** Two or three plain sentences defining the title, for a reader outside the domain. */
  tooltip: string
}

/**
 * What the answer to a kickstart question looks like: a verdict card on one
 * session, a Markdown table, a flowchart, or prose alone (`free`).
 */
export type RenderKind = "verdict" | "table" | "flowchart" | "free"

/** One kickstart question, shown as a button above the composer. */
export interface SuggestedAction {
  /**
   * What the answer looks like, shown as a glyph on the button.
   *
   * A promise to the reader about what pressing it will draw. What actually
   * delivers it is a literal phrase inside `action`; `checkSuggestedActions`
   * (`lib/site/kickstarts.ts`) refuses to let the two disagree.
   */
  render: RenderKind
  title: string
  label: string
  /** The full sentence actually sent to the agent when the button is pressed. */
  action: string
}

/** One recorded tool call of the session the home page shows. */
export interface ExhibitCall {
  /** The tool's name as the trace records it, such as `payments.refund`. */
  tool: string
  /** One sentence: what the call did. */
  did: string
  /** The auditor's mark in the margin. */
  mark: "clean" | "flagged"
  /** Set when the runtime did not let the call through, such as `denied`. */
  status?: string
  /** The policies the call broke; empty or absent for a clean call. */
  policies?: string[]
  /** A few handwritten words beside the line. */
  note?: string
}

export interface SiteConfig {
  brand: {
    displayName: string
    /** The wordmark, split so the two halves can be coloured differently. */
    logoPrefix: string
    logoAccent: string
    footerName: string
  }
  seo: {
    locale: string
    title: string
    description: string
    keywords: string[]
  }
  home: {
    tagline: string
    description: string
    /** One line describing what the data covers. */
    blurb: string
    techStack: string[]
    headline: { prefix: string; accent: string }
    cta: { title: string; subtitle: string }
    /** Labels for the overlay that renders `data/business-context.md`. */
    businessContext: { triggerLabel: string; title: string; subtitle: string }
    /**
     * One audited session, drawn call by call beside the headline
     * (app/(marketing)/_components/Exhibit.tsx). The verdict on it is the
     * agent's recorded answer; its heading is `chat.verdict.riskyLabel`.
     */
    exhibit: {
      label: string
      /** Read by screen readers for a tick, and for a cross. */
      cleanLabel: string
      flaggedLabel: string
      sessionId: string
      agent: string
      task: string
      severity: string
      policies: string[]
      caption: string
      calls: ExhibitCall[]
    }
  }
  /** The four business lines, shown on both the home page and the agent. */
  capabilities: Capability[]
  chat: {
    /** What the assistant calls itself in the chat UI. */
    agent: string
    welcomeSubtitle: string
    tryExamples: string
    suggestionsHint: string
    inputPlaceholder: string
    messages: {
      /** The whole sentence in the banner above the conversation, printed as-is. */
      welcomeMessage: string
      /** User submitted while a reply was still streaming. */
      waitForResponse: string
      /** The agent could not be called, or its answer could not be read. */
      agentUnavailable: string
      /** The question is longer than `MAX_PROMPT_CHARS` of lib/agent/contract.ts. */
      promptTooLong: string
      /** The reader asked more often than the hosted page allows (lib/agent/guard.ts). */
      rateLimited: string
      /** The request failed the bot check (lib/agent/guard.ts). */
      botBlocked: string
    }
    /** The words of a verdict card and of the refusal notice (components/chat/VerdictCard.tsx). */
    verdict: {
      riskyLabel: string
      cleanLabel: string
      /** Read by screen readers before the session ID. */
      sessionLabel: string
      policiesLabel: string
      categoriesLabel: string
      flaggedCallsLabel: string
      /** Before the models that wrote the answer a verdict belongs to. */
      judgedByLabel: string
      refusalTitle: string
    }
    suggestedActions: SuggestedAction[]
  }
}

/**
 * Every key `data/site.toml` must declare, as dotted paths.
 *
 * Checked by `load.ts` when Next.js reads the file, so a missing key fails the
 * build with the key's name instead of rendering an empty heading on a live
 * page. TOML is not type-checked, so this list is the only thing standing
 * between a typo and an `undefined` in production.
 */
export const REQUIRED_SITE_KEYS: readonly string[] = [
  "brand.displayName",
  "brand.logoPrefix",
  "brand.logoAccent",
  "brand.footerName",
  "seo.locale",
  "seo.title",
  "seo.description",
  "seo.keywords",
  "home.tagline",
  "home.description",
  "home.blurb",
  "home.techStack",
  "home.headline.prefix",
  "home.headline.accent",
  "home.cta.title",
  "home.cta.subtitle",
  "home.businessContext.triggerLabel",
  "home.businessContext.title",
  "home.businessContext.subtitle",
  "home.exhibit.label",
  "home.exhibit.cleanLabel",
  "home.exhibit.flaggedLabel",
  "home.exhibit.sessionId",
  "home.exhibit.agent",
  "home.exhibit.task",
  "home.exhibit.severity",
  "home.exhibit.policies",
  "home.exhibit.caption",
  "home.exhibit.calls",
  "capabilities",
  "chat.agent",
  "chat.welcomeSubtitle",
  "chat.tryExamples",
  "chat.suggestionsHint",
  "chat.inputPlaceholder",
  "chat.suggestedActions",
  "chat.messages.welcomeMessage",
  "chat.messages.waitForResponse",
  "chat.messages.agentUnavailable",
  "chat.messages.promptTooLong",
  "chat.messages.rateLimited",
  "chat.messages.botBlocked",
  "chat.verdict.riskyLabel",
  "chat.verdict.cleanLabel",
  "chat.verdict.sessionLabel",
  "chat.verdict.policiesLabel",
  "chat.verdict.categoriesLabel",
  "chat.verdict.flaggedCallsLabel",
  "chat.verdict.judgedByLabel",
  "chat.verdict.refusalTitle",
]
