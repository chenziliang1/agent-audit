"use client";

import type { UIMessage } from "ai";
import { motion } from "framer-motion";
import { User } from "lucide-react";
import { useState } from "react";

import { AssistantAvatar } from "./AssistantAvatar";
import { Markdown } from "./markdown";
import { RefusalNotice, VerdictCard } from "./VerdictCard";
import type { SiteConfig } from "@/lib/site/schema";
import { cn } from "@/lib/utils";

/**
 * Collapsible component for displaying reasoning/thinking content.
 * Shows a summary by default, expands to show full content on click.
 */
const ReasoningBlock = ({ text }: { text: string }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Truncate text for preview (first 100 chars)
  const previewText = text.length > 100 ? text.slice(0, 100) + "..." : text;

  return (
    <div className="overflow-hidden rounded-md border border-slate-300 bg-surface">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center gap-2 text-left cursor-pointer hover:bg-slate-100 transition-colors"
      >
        <svg
          className={cn(
            "w-4 h-4 text-slate-500 transition-transform",
            isExpanded && "rotate-90"
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-mono text-xs font-medium uppercase tracking-wider text-slate-700">
          Thinking
        </span>
        {!isExpanded && (
          <span className="text-xs text-slate-500 truncate flex-1">
            {previewText}
          </span>
        )}
      </button>
      {isExpanded && (
        <div className="px-3 py-2 border-t border-slate-200">
          <div className="text-xs text-slate-700 whitespace-pre-wrap">
            {text}
          </div>
        </div>
      )}
    </div>
  );
};

export const PreviewMessage = ({
  message,
  append,
  verdictLabels,
}: {
  message: UIMessage;
  append?: (message: any) => Promise<string | null | undefined>;
  /** The words of a verdict card; from `data/site.toml`, like all UI copy. */
  verdictLabels: SiteConfig["chat"]["verdict"];
}) => {
  return (
    <motion.div
      className="w-full mx-auto max-w-3xl group/message"
      initial={{ y: 5, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      data-role={message.role}
    >
      <div
        className={cn(
          "flex gap-3 w-full",
          message.role === "user" ? "justify-end" : "justify-start"
        )}
      >
        {message.role === "assistant" && <AssistantAvatar />}

        <div
          className={cn(
            "flex flex-col gap-2 rounded-md px-4 py-3.5",
            // An answer may take the whole row beside its avatar (2rem plus
            // the gap): a table of four columns needs the width. A question
            // stays narrower, so the two sides read apart, and breaks a word
            // longer than its bubble (a pasted ID or token) instead of
            // widening the page.
            message.role === "user"
              ? "min-w-0 max-w-[85%] break-words sm:max-w-[78%] bg-primary text-primary-foreground"
              : "min-w-0 max-w-[calc(100%-2.75rem)] border border-slate-300 bg-sheet"
          )}
        >
          {/* AI SDK v5: Use parts instead of content */}
          {message.parts && message.parts.length > 0 && (
            <div className="flex flex-col gap-4">
              {message.parts.map((part: any, index: number) => {
                // Render reasoning/thinking content
                if (part.type === 'reasoning' && part.text) {
                  return (
                    <ReasoningBlock key={index} text={part.text} />
                  );
                }
                // The agent's structured verdict on one session, and the
                // notice that replaces an answer the model declined to give.
                // Both arrive as data parts from /api/chat (lib/agent/message.ts).
                if (part.type === 'data-verdict' && part.data) {
                  return (
                    <VerdictCard
                      key={index}
                      verdict={part.data}
                      models={part.data.models}
                      labels={verdictLabels}
                    />
                  );
                }
                if (part.type === 'data-refusal' && part.data) {
                  return (
                    <RefusalNotice key={index} message={part.data.message} labels={verdictLabels} />
                  );
                }
                // Render text content
                if (part.type === 'text' && part.text) {
                  return (
                    <div
                      key={index}
                      className={cn(
                        message.role === "assistant"
                          ? "text-primary"
                          : "text-primary-foreground"
                      )}
                    >
                      <Markdown
                        onQuestionClick={(question) => {
                          append?.({
                            role: 'user',
                            content: question,
                          });
                        }}
                      >
                        {part.text}
                      </Markdown>
                    </div>
                  );
                }
                return null;
              })}
            </div>
          )}
        </div>

        {/* User Avatar - Right side */}
        {message.role === "user" && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-slate-300 bg-surface">
            <User className="h-4 w-4 text-slate-600" aria-label="You" />
          </div>
        )}
      </div>
    </motion.div>
  );
};

export const ThinkingMessage = () => {
  const role = "assistant";

  return (
    <motion.div
      className="w-full mx-auto max-w-3xl group/message"
      initial={{ y: 5, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { delay: 1 } }}
      data-role={role}
    >
      <div className="flex gap-3 w-full justify-start">
        <AssistantAvatar />

        <div className="rounded-md border border-slate-300 bg-sheet px-4 py-3.5">
          <div className="flex items-center gap-2.5 text-slate-600">
            <span className="inline-block h-2 w-2 rounded-full bg-accent animate-pulse motion-reduce:animate-none" />
            <span className="font-mono text-xs uppercase tracking-wider">Thinking...</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
