"use client";

import { useStorage } from "@/lib/storage";
import type { ParsedDoc } from "@/lib/types";
import { useMemo } from "react";

interface Props {
  doc: ParsedDoc;
}

export function ProgressBar({ doc }: Props) {
  const { questionMap, hydrated } = useStorage();
  const total = useMemo(
    () =>
      doc.sections.reduce(
        (n, s) => n + (s.content.kind === "questions" ? s.content.questions.length : 0),
        0,
      ),
    [doc],
  );
  const asked = useMemo(
    () => Object.values(questionMap).filter((q) => q.asked).length,
    [questionMap],
  );
  const pct = total === 0 ? 0 : Math.min(100, (asked / total) * 100);

  return (
    <div className="flex flex-col gap-1 min-w-0 flex-1">
      <div className="flex items-baseline justify-between gap-3 text-xs text-ink-muted">
        <span aria-live="polite" suppressHydrationWarning>
          {hydrated ? `${asked} of ${total} asked` : `${total} questions`}
        </span>
      </div>
      <div className="h-1 w-full bg-rule rounded-full overflow-hidden">
        <div
          className="h-full bg-accent transition-[width] duration-200"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
