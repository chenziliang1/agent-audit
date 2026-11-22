"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Menu, X } from "lucide-react"

/** One entry in the top bar. */
interface NavItem {
  label: string
  href: string
}

/**
 * The bar is the same on every page, and its two entries are the app's two
 * pages. Not authored copy: `data/` says what the app is about, not how
 * many pages it has.
 */
const DEFAULT_NAV_ITEMS: NavItem[] = [
  { label: "Home", href: "/" },
  { label: "Chat", href: "/chat" },
]

/**
 * The top bar: the wordmark, the two pages, and nothing else. It is a strip of
 * the same paper as the page, closed by one rule, so the first thing with any
 * weight on a page is that page's own heading.
 */
export default function Navigation({
  items = DEFAULT_NAV_ITEMS,
  logoPrefix,
  logoAccent,
}: {
  items?: NavItem[]
  /** The wordmark, split so the two halves can be set differently. */
  logoPrefix: string
  logoAccent: string
}) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const pathname = usePathname()

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/"
    }
    return pathname.startsWith(href)
  }

  return (
    <nav className="fixed left-0 right-0 top-0 z-50 border-b border-slate-300 bg-paper/95 backdrop-blur-sm">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Wordmark */}
          <Link
            href="/"
            className="flex items-baseline font-display text-xl font-bold tracking-[-0.02em] text-primary"
          >
            {logoPrefix}
            <span className="mx-[0.12em] inline-block h-[0.34em] w-[0.34em] rounded-full bg-accent" aria-hidden="true" />
            {logoAccent}
          </Link>

          {/* Desktop */}
          <div className="hidden items-center gap-7 md:flex">
            {items.map((item) => {
              const active = isActive(item.href)

              if (item.href === "/chat") {
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-brand"
                  >
                    Start Chat
                  </Link>
                )
              }

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`text-sm font-medium transition-colors ${
                    active
                      ? "text-primary underline decoration-accent decoration-2 underline-offset-8"
                      : "text-slate-600 hover:text-primary"
                  }`}
                >
                  {item.label}
                </Link>
              )
            })}
          </div>

          {/* Mobile */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="cursor-pointer p-2 text-slate-700 transition-colors hover:text-primary"
              aria-label="Toggle menu"
              aria-expanded={isMenuOpen}
            >
              {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {isMenuOpen && (
          <div className="border-t border-slate-300 md:hidden">
            <div className="space-y-1 py-3">
              {items.map((item) => {
                const active = isActive(item.href)

                if (item.href === "/chat") {
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="mt-2 block rounded-full bg-primary px-4 py-3 text-center text-base font-semibold text-primary-foreground"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Start Chat
                    </Link>
                  )
                }

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`block px-1 py-3 text-base font-medium transition-colors ${
                      active ? "text-primary" : "text-slate-600 hover:text-primary"
                    }`}
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {item.label}
                  </Link>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
