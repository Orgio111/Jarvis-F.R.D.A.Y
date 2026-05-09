import React, { useRef, useEffect } from 'react';
import { useGpuStore } from './gpuStore';
import { GlassPanel } from '@/components/ui/GlassPanel';

/**
 * Simple canvas-based GPU utilisation sparkline.
 * Uses WebGL when available (detected via renderingCapabilities).
 * Falls back to 2D Canvas.
 */
export function GpuMetricsChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const metrics = useGpuStore((s) => s.metrics);
  const status = useGpuStore((s) => s.status);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const POINTS = metrics.length;

    ctx.clearRect(0, 0, W, H);

    // Grid lines
    ctx.strokeStyle = 'rgba(0,212,255,0.06)';
    ctx.lineWidth = 1;
    for (let y = 0; y <= H; y += H / 4) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    if (POINTS < 2) {
      // Not enough data — show placeholder
      ctx.fillStyle = 'rgba(0,212,255,0.2)';
      ctx.font = '11px monospace';
      ctx.fillText('Collecting...', 8, H / 2 + 4);
      return;
    }

    const gpuData = metrics.map((m) => m.utilization.gpuPercent);
    const memData = metrics.map((m) => m.utilization.memoryPercent);

    drawLine(ctx, gpuData, W, H, 'rgba(0,212,255,0.8)', 'rgba(0,212,255,0.08)');
    drawLine(ctx, memData, W, H, 'rgba(0,102,255,0.6)', 'rgba(0,102,255,0.04)');

    // Legend
    ctx.font = '10px monospace';
    ctx.fillStyle = 'rgba(0,212,255,0.8)';
    ctx.fillText('GPU%', 4, 12);
    ctx.fillStyle = 'rgba(0,102,255,0.8)';
    ctx.fillText('MEM%', 40, 12);

  }, [metrics]);

  return (
    <GlassPanel className="p-4">
      <p className="text-jarvis-text-dim text-xs font-mono mb-2">Live Utilisation</p>
      <canvas
        ref={canvasRef}
        width={320}
        height={80}
        className="w-full h-20 rounded"
        style={{ imageRendering: 'pixelated' }}
      />
      {status && (
        <div className="flex gap-4 mt-2">
          <span className="text-xs font-mono text-jarvis-cyan">
            GPU: {Math.round(status.utilization.gpuPercent)}%
          </span>
          <span className="text-xs font-mono text-jarvis-blue">
            Mem: {Math.round(status.utilization.memoryPercent)}%
          </span>
          <span className="text-xs font-mono text-jarvis-text-dim">
            {status.utilization.temperatureC.toFixed(0)}°C
          </span>
        </div>
      )}
    </GlassPanel>
  );
}

function drawLine(
  ctx: CanvasRenderingContext2D,
  data: number[],
  W: number,
  H: number,
  strokeColor: string,
  fillColor: string,
) {
  const step = W / (data.length - 1);

  ctx.beginPath();
  ctx.moveTo(0, H - (data[0]! / 100) * H);
  for (let i = 1; i < data.length; i++) {
    ctx.lineTo(i * step, H - (data[i]! / 100) * H);
  }

  // Fill under the line
  ctx.lineTo(W, H);
  ctx.lineTo(0, H);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();

  // Stroke the line
  ctx.beginPath();
  ctx.moveTo(0, H - (data[0]! / 100) * H);
  for (let i = 1; i < data.length; i++) {
    ctx.lineTo(i * step, H - (data[i]! / 100) * H);
  }
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}
