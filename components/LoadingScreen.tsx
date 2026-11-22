/**
 * The full-page placeholder Next.js shows while a route segment loads.
 *
 * One component behind both `loading.tsx` files. They were two near-identical
 * copies differing only in the word under the spinner, which is exactly the
 * shape that drifts: a colour changed on one page and not the other.
 *
 * Colours come from the Tailwind theme rather than literals so the whole thing
 * follows a palette change.
 */
export function LoadingScreen({ label }: { label: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper">
      <div className="flex flex-col items-center gap-5">
        <div
          className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-primary motion-reduce:animate-none"
          aria-hidden="true"
        />
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-slate-600">{label}</p>
      </div>
    </div>
  )
}
