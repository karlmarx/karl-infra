import { categoryMeta } from '../data/automations';

export function Legend() {
  return (
    <div className="pointer-events-auto absolute bottom-4 left-4 z-10 rounded-lg border border-border bg-bg-2/90 p-3 text-[11px] shadow-xl backdrop-blur-md">
      <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-text-dim">
        Categories
      </div>
      <ul className="grid grid-cols-1 gap-1.5">
        {Object.values(categoryMeta).map((c) => (
          <li key={c.id} className="flex items-center gap-2 text-text">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: c.hex }}
              aria-hidden
            />
            <span>{c.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
