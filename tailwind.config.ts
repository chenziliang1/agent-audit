import type { Config } from "tailwindcss"

// This app is light-only: there is no theme toggle, so no `darkMode` strategy
// and no `dark:` variants anywhere in the tree.
const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      /* The palette: an auditor's desk. Ledger paper, ink, the red margin
       * line, a ballpoint pen.
       *
       *   paper / sheet   the green-tinted ledger page, and a sheet lying on it
       *   primary (ink)   text, dark surfaces, the user's message
       *   brand (pen)     the action colour: links, the send button, focus
       *                   rings, and the auditor's handwritten notes
       *   accent (margin) the red of a ledger's margin line: a violation, a
       *                   stamp, the rule under a heading
       *   tick            a call or a session that was checked and is clean
       *
       * `slate` is this design's neutral scale, not Tailwind's: every step is
       * re-tinted toward the paper, so a component that names `slate-500`
       * gets ink thinned with ledger green instead of a blue-grey. */
      colors: {
        paper: "#E7EFE5",
        sheet: "#FBFDF9",
        slate: {
          50: "#F4F8F2",
          100: "#E7EFE5",
          200: "#D2DFD1",
          300: "#B9CBB9",
          400: "#8FA596",
          500: "#6B8175",
          600: "#4C6156",
          700: "#35483E",
          800: "#223329",
          900: "#13241C",
        },
        /** Ink. Headings, body text, dark surfaces, the user bubble. */
        primary: {
          DEFAULT: "#13241C",
          foreground: "#FBFDF9",
        },
        /** Ballpoint blue. Links, the send button, focus rings, margin notes. */
        brand: {
          DEFAULT: "#2343B5",
          dark: "#1A3391", // hover on a filled surface
          light: "#4A67D0", // focus rings and hover borders
          soft: "#8FA2E6",
          wash: "#E1E7FA", // a tint behind pen-coloured text
          foreground: "#FFFFFF",
        },
        /** Margin red. A violation, a stamp, the short rule under a heading. */
        accent: {
          DEFAULT: "#BF3A30",
          wash: "#F7E1DD",
          foreground: "#FFFFFF",
        },
        /** A call or a session that was checked and found clean. */
        tick: {
          DEFAULT: "#1D7A4C",
          wash: "#D7ECDD",
        },
        /** Page and card backgrounds. */
        background: "#E7EFE5",
        foreground: "#13241C",
        surface: "#F4F8F2",
        border: "#D2DFD1", // what `@apply border-border` resolves to
        muted: {
          DEFAULT: "#E7EFE5",
          foreground: "#6B8175",
        },

        // shadcn/ui primitives. Kept whole because `components/ui/*` and any
        // component added with the shadcn CLI expect these exact names.
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      /* Four voices, each with one job:
       *
       *   display  headings and the wordmark
       *   body     everything a person reads as prose
       *   mono     what the audited systems wrote: tool names, IDs, policies
       *   hand     the auditor's margin notes on the home page's exhibit,
       *            and nowhere else
       */
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        heading: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        hand: ["var(--font-hand)", "cursive"],
      },
      /* The exhibit's one orchestrated moment: its rows are entered, then
       * marked, then stamped. `globals.css` switches all three off for a
       * reader who asked for reduced motion. */
      keyframes: {
        "row-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "mark-in": {
          from: { opacity: "0", transform: "scale(0.4)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "stamp-in": {
          "0%": { opacity: "0", transform: "rotate(-5deg) scale(1.6)" },
          "70%": { opacity: "1", transform: "rotate(-5deg) scale(0.96)" },
          "100%": { opacity: "1", transform: "rotate(-5deg) scale(1)" },
        },
      },
      animation: {
        "row-in": "row-in 0.35s ease-out both",
        "mark-in": "mark-in 0.25s ease-out both",
        "stamp-in": "stamp-in 0.4s cubic-bezier(0.2, 0.9, 0.3, 1) both",
      },
      /* Radius is a size ladder, and each step names a role:
       *
       *   rounded-full   pill     the nav's chat button, the modal's close button
       *   rounded-lg     sheet    a page lying on the desk: the exhibit, the
       *                           chat's welcome sheet, the modal
       *   rounded-md     block    a message, a verdict card, the composer, a
       *                           code block, a diagram, a kickstart button
       *   rounded-sm     tag      policy and call chips, a stamp, the avatar
       *
       * Nothing is extended here: these are Tailwind's own steps.
       */
    },
  },
  plugins: [require("tailwindcss-animate")],
}

export default config
