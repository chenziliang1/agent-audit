import type { RenderKind, SuggestedAction } from "./schema"

/**
 * The rules the kickstart questions of `data/site.toml` must keep, as a plain
 * function: `lib/site/load.ts` runs it when the file is read, so a broken set
 * fails `mise run build-web`, and `tests_node/` runs it on its own.
 *
 * A kickstart's `render` field draws a glyph on its button: a promise about
 * what the answer will look like. Nothing in the UI makes the agent keep that
 * promise; what does is a phrase inside the question itself. So the two are
 * checked against each other here, in both directions: a question marked
 * `table` must ask for a table, and a question that asks for a table must be
 * marked `table`.
 *
 * Only erasable syntax and no runtime import, so Node runs this file as it is.
 */

/** How many kickstart questions the chat page shows. */
export const KICKSTART_COUNT = 12

/** How many questions each render kind gets. */
export const KICKSTARTS_PER_KIND = 3

/** The phrase that makes the agent audit a session, and so return a verdict card. */
const VERDICT_PHRASE = "Audit session ses_"
/** The phrase that makes the agent answer with a Markdown table. */
const TABLE_PHRASE = "as a Markdown table"
/** The phrase that makes the agent answer with a ```mermaid block, which the chat draws. */
const FLOWCHART_PHRASE = "as a Mermaid flowchart"

const KINDS: readonly RenderKind[] = ["verdict", "table", "flowchart", "free"]

/**
 * The render kind the wording of `action` will produce.
 *
 * A flowchart of a session also audits it, so its answer carries a verdict card
 * too; the flowchart is the larger promise and wins.
 */
export function renderKindOf(action: string): RenderKind {
  if (action.includes(FLOWCHART_PHRASE)) return "flowchart"
  if (action.includes(TABLE_PHRASE)) return "table"
  if (action.includes(VERDICT_PHRASE)) return "verdict"
  return "free"
}

/**
 * What is wrong with `actions`, one sentence per problem; empty when nothing is.
 *
 * Checked: there are exactly `KICKSTART_COUNT` of them, every `render` is a
 * known kind and is the kind the question's wording produces, a question asks
 * for one block and not two, and each kind appears `KICKSTARTS_PER_KIND` times.
 */
export function checkSuggestedActions(actions: readonly SuggestedAction[]): string[] {
  const problems: string[] = []
  if (actions.length !== KICKSTART_COUNT) {
    problems.push(`there are ${actions.length} kickstart questions, not ${KICKSTART_COUNT}`)
  }
  for (const action of actions) {
    const name = `"${action.title}"`
    if (!KINDS.includes(action.render)) {
      problems.push(`${name} has the unknown render "${action.render}"`)
      continue
    }
    if (action.action.includes(TABLE_PHRASE) && action.action.includes(FLOWCHART_PHRASE)) {
      problems.push(`${name} asks for both a table and a flowchart`)
      continue
    }
    const worded = renderKindOf(action.action)
    if (worded !== action.render) {
      problems.push(`${name} is marked "${action.render}" but its wording produces "${worded}"`)
    }
  }
  for (const kind of KINDS) {
    const count = actions.filter((action) => action.render === kind).length
    if (count !== KICKSTARTS_PER_KIND) {
      problems.push(`${count} questions are marked "${kind}", not ${KICKSTARTS_PER_KIND}`)
    }
  }
  return problems
}
