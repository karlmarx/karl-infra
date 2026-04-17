import type { AutomationNode } from '../data/automations';
import { categoryMeta } from '../data/automations';

interface Props {
  node: AutomationNode | null;
  onClose: () => void;
}

export function DetailsPanel({ node, onClose }: Props) {
  if (!node) return null;
  const meta = categoryMeta[node.category];

  return (
    <aside
      className="pointer-events-auto absolute right-4 top-4 z-20 flex w-[340px] max-w-[90vw] flex-col gap-3 rounded-lg border border-border bg-bg-2/95 p-4 shadow-2xl backdrop-blur-md"
      role="dialog"
      aria-label={`${node.label} details`}
    >
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: meta.hex }}
            />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">
              {meta.label}
            </span>
          </div>
          <h2 className="mt-1 text-base font-semibold text-text-strong">
            {node.label}
          </h2>
          {node.sublabel && (
            <div className="text-xs text-text-dim">{node.sublabel}</div>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close details"
          className="shrink-0 rounded border border-border px-2 py-1 text-xs text-text-dim transition-colors hover:border-border-strong hover:text-text-strong"
        >
          esc
        </button>
      </header>

      <p className="text-[13px] leading-relaxed text-text">{node.description}</p>

      <dl className="grid grid-cols-[90px_1fr] gap-x-3 gap-y-1.5 text-[12px]">
        {node.schedule && (
          <>
            <dt className="text-text-dim">Schedule</dt>
            <dd className="font-mono text-text-strong">{node.schedule}</dd>
          </>
        )}
        {node.script && (
          <>
            <dt className="text-text-dim">Script</dt>
            <dd className="break-all font-mono text-text-strong">{node.script}</dd>
          </>
        )}
        {node.stack && (
          <>
            <dt className="text-text-dim">Stack</dt>
            <dd className="text-text-strong">{node.stack}</dd>
          </>
        )}
        {node.repo && (
          <>
            <dt className="text-text-dim">Repo</dt>
            <dd className="font-mono text-text-strong">{node.repo}</dd>
          </>
        )}
        {node.url && (
          <>
            <dt className="text-text-dim">URL</dt>
            <dd className="break-all">
              <a
                href={node.url}
                target="_blank"
                rel="noreferrer"
                className="font-mono text-purple-300 underline decoration-dotted underline-offset-2 hover:text-purple-200"
              >
                {node.url.replace(/^https?:\/\//, '')}
              </a>
            </dd>
          </>
        )}
      </dl>

      {node.notes && node.notes.length > 0 && (
        <div>
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-text-dim">
            Notes
          </div>
          <ul className="list-disc space-y-1 pl-4 text-[12px] text-text">
            {node.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
