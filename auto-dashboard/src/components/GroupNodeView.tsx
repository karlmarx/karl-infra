import type { Node, NodeProps } from '@xyflow/react';
import type { GroupBox } from '../data/automations';
import { categoryMeta } from '../data/automations';

export type GroupFlowNode = Node<{ group: GroupBox }, 'group'>;

/**
 * Renders a labeled rectangle that sits behind a cluster of automation nodes.
 * Non-interactive — it exists purely for visual grouping and wayfinding.
 */
export function GroupNodeView({ data }: NodeProps<GroupFlowNode>) {
  const g = data.group;
  const meta = categoryMeta[g.category];

  return (
    <div
      className="pointer-events-none relative h-full w-full rounded-lg border"
      style={{
        width: g.width,
        height: g.height,
        borderColor: `${meta.hex}40`,
        background: `linear-gradient(160deg, ${meta.hex}0a 0%, transparent 70%)`,
      }}
    >
      <div
        className="absolute left-3 top-2 flex flex-col"
        style={{ color: meta.hex }}
      >
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em]">
          {g.label}
        </span>
        {g.sublabel && (
          <span className="text-[10px] font-normal normal-case tracking-normal opacity-70">
            {g.sublabel}
          </span>
        )}
      </div>
    </div>
  );
}
