import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

/**
 * The square that marks a message as the agent's.
 *
 * Three places show it: the banner above the conversation, every assistant
 * message, and the "thinking" placeholder. One component so they cannot drift
 * into three slightly different squares.
 *
 * It is the auditor's tick on ink: the mark the home page puts beside a call
 * it has read. A glyph rather than the agent's name from `site.toml`: it has
 * to fit a 32px box, and `site.toml` is free to name the agent something long.
 */
export function AssistantAvatar({ size = "sm" }: { size?: "sm" | "md" }) {
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-sm bg-primary",
        size === "md" ? "h-10 w-10" : "h-8 w-8",
      )}
      aria-hidden="true"
    >
      <Check
        className={cn("text-primary-foreground", size === "md" ? "h-5 w-5" : "h-4 w-4")}
        strokeWidth={3}
      />
    </div>
  )
}
