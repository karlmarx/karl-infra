import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import type { AutomationNode } from '../data/automations';
import { categoryMeta } from '../data/automations';

export type AutomationFlowNode = Node<
  { automation: AutomationNode; isSelected: boolean },
  'automation'
>;

/**
 * A single automation node. Card-style with a colored left border that reflects
 * the category. Click handling is wired at the ReactFlow level (onNodeClick),
 * so this component is purely presentational.
 */
export function AutomationNodeView({
  data,
  selected,
}: NodeProps<AutomationFlowNode>) {
  const a = data.automation;
  const meta = categoryMeta[a.category];
  const isSelf = a.category === 'self';

  return (
    <div
      className={[
        'relative min-w-[190px] max-w-[220px] rounded-md border bg-bg-2/95 px-3 py-2',
        'shadow-lg backdrop-blur-sm transition-all',
        selected
          ? 'ring-2 ring-offset-2 ring-offset-bg ring-accent'
          : 'hover:-translate-y-[1px] hover:shadow-xl',
        isSelf ? 'border-pink-500/60' : 'border-border',
      ].join(' ')}
      style={{
        borderLeftWidth: 4,
        borderLeftColor: meta.hex,
        // when selected, use the accent; otherwise keep the default border
        // @ts-expect-error -- inline custom property
        '--tw-ring-color': meta.hex,
      }}
      title={a.description}
    >
      <Handle type="target" position={Position.Left} />
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-[13px] font-semibold text-text-strong">
            {a.label}
          </div>
          {a.sublabel && (
            <div className="truncate text-[11px] text-text-dim">{a.sublabel}</div>
          )}
        </div>
        {a.schedule && (
          <span
            className="shrink-0 rounded-sm border border-border px-1 py-[1px] text-[9px] font-mono uppercase tracking-wider text-text-dim"
            title="Cron / schedule"
          >
            {a.schedule.length > 14 ? 'cron' : a.schedule}
          </span>
        )}
      </div>
      {isSelf && (
        <div className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-pink-400">
          you are here
        </div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
