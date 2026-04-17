export function Header({ count }: { count: { nodes: number; edges: number } }) {
  return (
    <header className="pointer-events-none absolute left-4 top-4 z-10 flex flex-col gap-1">
      <div className="pointer-events-auto rounded-lg border border-border bg-bg-2/85 px-4 py-3 shadow-xl backdrop-blur-md">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg font-semibold text-text-strong">
            auto.93.fyi
          </h1>
          <span className="font-mono text-[10px] uppercase tracking-widest text-text-dim">
            Karl's automation map
          </span>
        </div>
        <p className="mt-1 max-w-md text-[12px] leading-relaxed text-text-dim">
          Interactive map of every automation across the Mac Studio, seedbox,
          Windows workstation, GitHub Actions, and Vercel. Click a node for
          details. Scroll to zoom, drag to pan.
        </p>
        <div className="mt-2 flex items-center gap-3 text-[10px] font-mono text-text-dim">
          <span>{count.nodes} nodes</span>
          <span className="text-border-strong">·</span>
          <span>{count.edges} edges</span>
        </div>
      </div>
    </header>
  );
}
