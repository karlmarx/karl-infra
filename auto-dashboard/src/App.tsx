import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeMouseHandler,
  type NodeTypes,
} from '@xyflow/react';

import {
  categoryMeta,
  edges as rawEdges,
  groups,
  nodes as rawNodes,
  type AutomationNode,
} from './data/automations';
import { AutomationNodeView } from './components/AutomationNodeView';
import { GroupNodeView } from './components/GroupNodeView';
import { DetailsPanel } from './components/DetailsPanel';
import { Legend } from './components/Legend';
import { Header } from './components/Header';

const nodeTypes: NodeTypes = {
  automation: AutomationNodeView,
  group: GroupNodeView,
};

function buildFlowNodes(selectedId: string | null): Node[] {
  const groupNodes: Node[] = groups.map((g) => ({
    id: `group-${g.id}`,
    type: 'group',
    position: { x: g.x, y: g.y },
    data: { group: g },
    // Force these to render behind everything and never be interactive.
    selectable: false,
    draggable: false,
    focusable: false,
    zIndex: 0,
    style: { width: g.width, height: g.height },
  }));

  const automationNodes: Node[] = rawNodes.map((a) => ({
    id: a.id,
    type: 'automation',
    position: a.position,
    data: { automation: a, isSelected: selectedId === a.id },
    selected: selectedId === a.id,
    zIndex: 1,
  }));

  return [...groupNodes, ...automationNodes];
}

function buildFlowEdges(selectedId: string | null): Edge[] {
  return rawEdges.map((e) => {
    const touchesSelected =
      selectedId !== null && (e.source === selectedId || e.target === selectedId);
    const sourceNode = rawNodes.find((n) => n.id === e.source);
    const color = sourceNode ? categoryMeta[sourceNode.category].hex : '#6b7280';
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: touchesSelected || e.animated || false,
      style: {
        stroke: touchesSelected ? color : `${color}77`,
        strokeWidth: touchesSelected ? 2.2 : 1.3,
      },
      labelStyle: {
        fill: '#cbd5e1',
        fontSize: 11,
      },
      labelBgStyle: {
        fill: '#0b0d12',
        fillOpacity: 0.85,
      },
      labelBgPadding: [4, 2] as [number, number],
      labelBgBorderRadius: 3,
      markerEnd: {
        type: 'arrowclosed' as const,
        color: touchesSelected ? color : `${color}aa`,
        width: 16,
        height: 16,
      },
      zIndex: touchesSelected ? 2 : 1,
    };
  });
}

function Inner() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const flowNodes = useMemo(() => buildFlowNodes(selectedId), [selectedId]);
  const flowEdges = useMemo(() => buildFlowEdges(selectedId), [selectedId]);

  const selectedAutomation: AutomationNode | null = useMemo(() => {
    if (!selectedId) return null;
    return rawNodes.find((n) => n.id === selectedId) ?? null;
  }, [selectedId]);

  const onNodeClick: NodeMouseHandler = useCallback((_evt, node) => {
    if (node.type !== 'automation') return;
    setSelectedId((prev) => (prev === node.id ? null : node.id));
  }, []);

  const onPaneClick = useCallback(() => setSelectedId(null), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSelectedId(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.25}
        maxZoom={2}
        proOptions={{ hideAttribution: false }}
        defaultEdgeOptions={{ type: 'default' }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="#1e2636"
        />
        <Controls
          position="bottom-right"
          showInteractive={false}
        />
        <MiniMap
          pannable
          zoomable
          position="top-right"
          nodeStrokeWidth={2}
          nodeColor={(n) => {
            if (n.type !== 'automation') return 'transparent';
            const data = n.data as { automation: AutomationNode };
            return categoryMeta[data.automation.category].hex;
          }}
          nodeBorderRadius={4}
          maskColor="rgba(11, 13, 18, 0.75)"
          style={{ width: 200, height: 140 }}
        />
      </ReactFlow>

      <Header count={{ nodes: rawNodes.length, edges: rawEdges.length }} />
      <Legend />
      <DetailsPanel node={selectedAutomation} onClose={() => setSelectedId(null)} />
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <Inner />
    </ReactFlowProvider>
  );
}
