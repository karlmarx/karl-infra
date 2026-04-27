"use client";

interface Props {
  value: string;
  onChange: (next: string) => void;
}

export function SearchBar({ value, onChange }: Props) {
  return (
    <div className="relative flex-1">
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search questions…"
        className="w-full rounded-md border border-rule bg-surface px-3 py-2 pr-9 text-sm focus:border-accent"
        aria-label="Search questions"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Clear search"
          className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 grid place-items-center text-ink-muted hover:text-ink"
        >
          ✕
        </button>
      )}
    </div>
  );
}
