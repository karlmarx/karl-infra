"use client";

import type { Section } from "@/lib/types";
import { useEffect, useState } from "react";

interface Props {
  sections: Section[];
}

export function SectionNav({ sections }: Props) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const handleNav = () => setOpen(false);

  return (
    <>
      <nav className="hidden lg:block sticky top-32 self-start no-print">
        <div className="text-xs uppercase tracking-wide text-ink-muted mb-2">
          Sections
        </div>
        <ul className="flex flex-col gap-1.5 text-sm">
          {sections.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                className="block text-ink-muted hover:text-accent leading-snug"
              >
                {s.title}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open sections"
        className="lg:hidden fixed right-4 bottom-4 z-30 h-12 w-12 rounded-full bg-accent text-white shadow-lg grid place-items-center text-2xl no-print"
      >
        ≡
      </button>

      {open && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/40 no-print"
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Sections"
        >
          <div
            className="absolute bottom-0 left-0 right-0 max-h-[80vh] bg-surface rounded-t-2xl p-5 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm uppercase tracking-wide text-ink-muted">
                Sections
              </span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="h-8 w-8 grid place-items-center text-ink-muted"
              >
                ✕
              </button>
            </div>
            <ul className="flex flex-col gap-3">
              {sections.map((s) => (
                <li key={s.id}>
                  <a
                    href={`#${s.id}`}
                    onClick={handleNav}
                    className="block text-base text-ink leading-snug"
                  >
                    {s.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </>
  );
}
