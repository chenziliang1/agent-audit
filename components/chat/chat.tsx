"use client";

import { AssistantAvatar } from "./AssistantAvatar";
import { PreviewMessage, ThinkingMessage } from "./message";
import { MultimodalInput } from "./multimodal-input";
import { Overview } from "./overview";
import { useScrollToBottom } from "@/hooks/use-scroll-to-bottom";
import { useChat } from "@ai-sdk/react";
import { toast } from "sonner";
import { X } from "lucide-react";
import { useState, useEffect } from "react";
import type { SiteConfig } from "@/lib/site/schema";

export function Chat({ site }: { site: SiteConfig }) {
  const [input, setInput] = useState("");
  const [isContextBannerVisible, setIsContextBannerVisible] = useState(true);

  const {
    messages,
    sendMessage,
    status,
    stop,
  } = useChat({
    // A refusal by the model is not an error: /api/chat answers it with an
    // ordinary message part. Anything reaching here is a rejected request or a
    // failed call to the agent, already worded for the reader by the route.
    onError: (error) => toast.error(error.message),
  });

  const isLoading = status === "streaming" || status === "submitted";

  const handleSubmit = (e?: { preventDefault?: () => void }) => {
    e?.preventDefault?.();
    if (input.trim()) {
      sendMessage({ text: input });
      setInput("");
    }
  };

  const append = async (message: any): Promise<string | null | undefined> => {
    if (message.content) {
      await sendMessage({ text: message.content });
      return null;
    } else if (message.text) {
      await sendMessage({ text: message.text });
      return null;
    }
    return null;
  };

  const [messagesContainerRef, messagesEndRef] =
    useScrollToBottom<HTMLDivElement>();

  useEffect(() => {
    if (messagesEndRef.current && messages.length > 0) {
      requestAnimationFrame(() => {
        messagesEndRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "end"
        });
      });
    }
  }, [messages.length]);

  return (
    <div className="flex flex-col min-w-0 h-[calc(100dvh-64px)] bg-paper">
      <div
        ref={messagesContainerRef}
        className="flex flex-col min-w-0 gap-4 flex-1 overflow-y-scroll pt-4 px-4"
      >
        {/* Initial AI Assistant Welcome Display */}
        {messages.length === 0 && <Overview site={site} />}

        {/* Context Banner */}
        {messages.length > 0 && isContextBannerVisible && (
          <div className="max-w-3xl mx-auto w-full">
            <div className="rounded-md border border-slate-300 bg-sheet p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  <AssistantAvatar size="md" />
                  <div className="flex-1">
                    <h3 className="font-display text-sm font-semibold text-primary">{site.chat.agent}</h3>
                    <p className="mt-1 text-xs text-slate-600">
                      {site.chat.messages.welcomeMessage}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setIsContextBannerVisible(false)}
                  className="shrink-0 cursor-pointer text-slate-500 transition-colors hover:text-primary"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((message) => (
          <PreviewMessage
            key={message.id}
            message={message}
            append={append}
            verdictLabels={site.chat.verdict}
          />
        ))}

        {isLoading &&
          messages.length > 0 &&
          messages[messages.length - 1].role === "user" && <ThinkingMessage />}

        {/* Auto-scroll anchor */}
        <div
          ref={messagesEndRef}
          className="shrink-0 min-w-[24px] min-h-[24px]"
        />
      </div>

      <div className="border-t border-slate-300 bg-surface p-4">
        <form className="flex mx-auto gap-2 w-full md:max-w-3xl">
          <MultimodalInput
            site={site}
            input={input}
            setInput={setInput}
            handleSubmit={handleSubmit}
            isLoading={isLoading}
            stop={stop}
            messages={messages}
            append={append}
          />
        </form>
      </div>
    </div>
  );
}
