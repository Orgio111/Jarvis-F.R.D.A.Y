/**
 * GraphCanvas — zero-dependency force-directed graph renderer using Canvas API.
 * Implements a simple Verlet integration with spring + repulsion forces.
 */
import React, { useRef, useEffect, useCallback } from 'react';
import type { GraphNode, GraphEdge } from './useObsidian';

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
}

const NODE_COLORS: Record<string, string> = {
  agent:       '#3b82f6', // blue
  swarm:       '#8b5cf6', // purple
  memory:      '#10b981', // green
  task:        '#f59e0b', // amber
  improvement: '#ef4444', // red
  note:        '#6b7280', // gray
};

const NODE_RADIUS = 6;
const LINK_DIST   = 100;
const REPULSION   = 3000;
const SPRING_K    = 0.05;
const DAMPING     = 0.85;
const CENTER_PULL = 0.002;

function initPositions(nodes: GraphNode[], w: number, h: number): GraphNode[] {
  return nodes.map((n, i) => {
    const angle = (i / nodes.length) * 2 * Math.PI;
    const r = Math.min(w, h) * 0.3;
    return {
      ...n,
      x: n.x ?? w / 2 + r * Math.cos(angle) + (Math.random() - 0.5) * 40,
      y: n.y ?? h / 2 + r * Math.sin(angle) + (Math.random() - 0.5) * 40,
      vx: 0,
      vy: 0,
    };
  });
}

export const GraphCanvas: React.FC<Props> = ({ nodes, edges, onNodeClick }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef   = useRef<number>(0);
  const simNodes  = useRef<GraphNode[]>([]);
  const dragging   = useRef<{ node: GraphNode; ox: number; oy: number } | null>(null);
  const hoveredId  = useRef<string | null>(null);

  const tick = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const w = canvas.width;
    const h = canvas.height;
    const ns = simNodes.current;
    if (!ns.length) return;

    const idxMap = new Map(ns.map((n, i) => [n.id, i]));

    // Repulsion
    for (let i = 0; i < ns.length; i++) {
      for (let j = i + 1; j < ns.length; j++) {
        const dx = ns[j].x! - ns[i].x!;
        const dy = ns[j].y! - ns[i].y!;
        const d2 = dx * dx + dy * dy + 0.01;
        const force = REPULSION / d2;
        const fx = (dx / Math.sqrt(d2)) * force;
        const fy = (dy / Math.sqrt(d2)) * force;
        ns[i].vx! -= fx;
        ns[i].vy! -= fy;
        ns[j].vx! += fx;
        ns[j].vy! += fy;
      }
    }

    // Spring forces along edges
    for (const e of edges) {
      const si = idxMap.get(e.source);
      const ti = idxMap.get(e.target);
      if (si === undefined || ti === undefined) continue;
      const dx = ns[ti].x! - ns[si].x!;
      const dy = ns[ti].y! - ns[si].y!;
      const d  = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const stretch = d - LINK_DIST;
      const fx = (dx / d) * stretch * SPRING_K;
      const fy = (dy / d) * stretch * SPRING_K;
      ns[si].vx! += fx;
      ns[si].vy! += fy;
      ns[ti].vx! -= fx;
      ns[ti].vy! -= fy;
    }

    // Center pull + Verlet integration
    for (const n of ns) {
      if (dragging.current?.node.id === n.id) continue;
      n.vx! = (n.vx! + (w / 2 - n.x!) * CENTER_PULL) * DAMPING;
      n.vy! = (n.vy! + (h / 2 - n.y!) * CENTER_PULL) * DAMPING;
      n.x! += n.vx!;
      n.y! += n.vy!;
      n.x! = Math.max(NODE_RADIUS, Math.min(w - NODE_RADIUS, n.x!));
      n.y! = Math.max(NODE_RADIUS, Math.min(h - NODE_RADIUS, n.y!));
    }

    draw(canvas, ns);
    animRef.current = requestAnimationFrame(tick);
  }, [edges]);

  const draw = (canvas: HTMLCanvasElement, ns: GraphNode[]) => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    const idxMap = new Map(ns.map((n, i) => [n.id, i]));

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, w, h);

    // Draw edges
    ctx.lineWidth = 0.8;
    for (const e of edges) {
      const si = idxMap.get(e.source);
      const ti = idxMap.get(e.target);
      if (si === undefined || ti === undefined) continue;
      const s = ns[si];
      const t = ns[ti];
      ctx.beginPath();
      ctx.moveTo(s.x!, s.y!);
      ctx.lineTo(t.x!, t.y!);
      ctx.strokeStyle = 'rgba(100,120,160,0.25)';
      ctx.stroke();
    }

    // Draw nodes
    for (const n of ns) {
      const r = NODE_RADIUS + (n.size > 500 ? 3 : n.size > 200 ? 2 : 0);
      const color = NODE_COLORS[n.type] ?? NODE_COLORS.note;
      const isHovered = n.id === hoveredId.current;

      ctx.beginPath();
      ctx.arc(n.x!, n.y!, r + (isHovered ? 3 : 0), 0, Math.PI * 2);
      ctx.fillStyle = isHovered ? '#fff' : color;
      ctx.fill();

      if (isHovered) {
        ctx.beginPath();
        ctx.arc(n.x!, n.y!, r + 6, 0, Math.PI * 2);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Label on hover or for large nodes
      if (isHovered || n.size > 1000) {
        ctx.font = '10px monospace';
        ctx.fillStyle = isHovered ? '#fff' : 'rgba(200,210,230,0.7)';
        ctx.fillText(n.label, n.x! + r + 4, n.y! + 4);
      }
    }
  };

  // Init simulation when nodes/edges change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !nodes.length) return;
    simNodes.current = initPositions(nodes, canvas.width, canvas.height);
    cancelAnimationFrame(animRef.current);
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [nodes, edges, tick]);

  // Mouse interactions
  const getNodeAt = (x: number, y: number): GraphNode | null => {
    for (const n of simNodes.current) {
      const dx = n.x! - x;
      const dy = n.y! - y;
      if (dx * dx + dy * dy <= (NODE_RADIUS + 4) ** 2) return n;
    }
    return null;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (dragging.current) {
      dragging.current.node.x = x;
      dragging.current.node.y = y;
      dragging.current.node.vx = 0;
      dragging.current.node.vy = 0;
    }
    const node = getNodeAt(x, y);
    hoveredId.current = node?.id ?? null;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const node = getNodeAt(e.clientX - rect.left, e.clientY - rect.top);
    if (node) {
      dragging.current = { node, ox: e.clientX, oy: e.clientY };
    }
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (dragging.current) {
      const dx = e.clientX - dragging.current.ox;
      const dy = e.clientY - dragging.current.oy;
      if (Math.abs(dx) < 4 && Math.abs(dy) < 4) {
        onNodeClick?.(dragging.current.node);
      }
      dragging.current = null;
    }
  };

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={500}
      className="w-full h-full rounded-lg cursor-crosshair"
      style={{ background: '#0f172a' }}
      onMouseMove={handleMouseMove}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => { hoveredId.current = null; dragging.current = null; }}
    />
  );
};
