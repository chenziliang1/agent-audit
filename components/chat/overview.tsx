import { motion } from "framer-motion";

import CapabilityCard from "@/components/CapabilityCard";
import type { SiteConfig } from "@/lib/site/schema";

import { AssistantAvatar } from "./AssistantAvatar";

/**
 * What an empty chat shows: who is answering, and the four things it looks
 * for. A blank sheet of the same paper the home page's audit is drawn on,
 * headed the way that one is.
 */
export const Overview = ({ site }: { site: SiteConfig }) => {
  const { chat, capabilities } = site;

  return (
    <motion.div
      key="overview"
      className="mx-auto w-full max-w-3xl md:mt-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ delay: 0.15 }}
    >
      <div className="rounded-lg border border-slate-300 bg-sheet">
        <div className="flex items-start gap-4 px-5 py-5 sm:px-6">
          <AssistantAvatar size="md" />
          <div>
            <h2 className="font-display text-2xl font-bold tracking-[-0.02em] text-primary">
              {chat.agent}
            </h2>
            <p className="mt-1 text-sm text-slate-600">{chat.welcomeSubtitle}</p>
          </div>
        </div>

        {/* The same four the home page shows, from the same `[[capabilities]]`.
            Two arrays here is how the two screens drifted apart last time.
            The rules between the cells are the grid's gaps showing through. */}
        <div className="grid grid-cols-2 gap-px border-y border-slate-200 bg-slate-200">
          {capabilities.map((capability, index) => (
            <CapabilityCard
              key={capability.title}
              capability={capability}
              align={index % 2 === 0 ? "start" : "end"}
              compact
              className="h-full bg-sheet"
            />
          ))}
        </div>

        <p className="px-5 py-3.5 font-mono text-xs leading-relaxed text-slate-600 sm:px-6">
          {chat.tryExamples}
        </p>
      </div>
    </motion.div>
  );
};
