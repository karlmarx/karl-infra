"use client";

import { useStorage } from "@/lib/storage";
import type { ChecklistItem } from "@/lib/types";

interface Props {
  item: ChecklistItem;
}

export function ChecklistItemCard({ item }: Props) {
  const { hydrated, isChecked, setChecked } = useStorage();
  const checked = isChecked(item.id);

  return (
    <label
      id={item.id}
      className={`flex items-start gap-3 rounded-md border border-rule bg-surface px-3.5 py-3 cursor-pointer min-h-14 select-none scroll-mt-32 ${
        hydrated && checked ? "opacity-60" : ""
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={!hydrated}
        onChange={(e) => setChecked(item.id, e.target.checked)}
        className="mt-1 h-5 w-5 accent-accent shrink-0"
      />
      <div className="flex-1">
        {item.title && (
          <div className="font-medium text-ink leading-snug">{item.title}</div>
        )}
        <div
          className={`text-ink-muted leading-relaxed ${
            item.title ? "text-sm mt-0.5" : "text-base"
          }`}
        >
          {item.body}
        </div>
      </div>
    </label>
  );
}
