import { useRef, useEffect } from 'react';
import { m } from 'framer-motion';
import { Cpu, Activity, Thermometer } from 'lucide-react';
import { useGpuStore } from './gpuStore';
import { GlassPanel } from '@/components/ui/GlassPanel';

/**
 * Enhanced canvas-based GPU utilisation sparkline with glow effects.
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

    // Clear with slight background
    ctx.clearRect(0, 0, W, H);

    // Grid lines
    ctx.strokeStyle = 'rgba(0,212,255,0.05)';
    ctx.lineWidth = 1;
    for (let y = 0; y <= H; y += H / 4) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    if (POINTS < 2) {
      ctx.fillStyle = 'rgba(0,212,255,0.15)';
      ctx.font = '11px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Collecting data...', W / 2, H / 2 + 4);
      return;
    }

    const gpuData = metrics.map((m) => m.utilization.gpuPercent);
    const memData = metrics.map((m) => m.utilization.memoryPercent);

    drawLine(ctx, gpuData, W, H, 'rgba(0,212,255,0.9)', 'rgba(0,212,255,0.08)', 'rgba(0,212,255,0.03)');
    drawLine(ctx, memData, W, H, 'rgba(0,102,255,0.7)', 'rgba(0,102,255,0.06)', 'rgba(0,102,255,0.02)');

    // Legend
    ctx.textAlign = 'left';
    ctx.font = '10px monospace';
    ctx.fillStyle = 'rgba(0,212,255,0.8)';
    ctx.fillText('GPU%', 6, 12);
    ctx.fillStyle = 'rgba(0,102,255,0.8)';
    ctx.fillText('MEM%', 44, 12);
  }, [metrics]);

  return (
    <m.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <GlassPanel className="p-5" hover glow>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-jarvis-cyan" />
            <span className="text-jarvis-text-dim text-xs font-mono">Live Utilization</span>
          </div>
          {status && (
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-jarvis-cyan">
                <Cpu size={10} className="inline mr-1" />
                {Math.round(status.utilization.gpuPercent)}%
              </span>
              <span className="text-xs font-mono text-jarvis-blue">
                {Math.round(status.utilization.memoryPercent)}%
              </span>
              <span className="text-xs font-mono text-jarvis-text-dim">
                <Thermometer size={10} className="inline mr-1" />
                {status.utilization.temperatureC.toFixed(0)}°C
              </span>
            </div>
          )}
        </div>
        <canvas
          ref={canvasRef}
          width={400}
          height={100}
          className="w-full h-24 rounded-lg"
          style={{ imageRendering: 'pixelated' }}
        />
      </GlassPanel>
    </m.div>
  );
}

function drawLine(
  ctx: CanvasRenderingContext2D,
  data: number[],
  W: number,
  H: number,
  strokeColor: string,
  fillColor1: string,
  fillColor2: string,
) {
  const step = W / (data.length - 1);

  // Gradient fill
  const gradient = ctx.createLinearGradient(0, 0, 0, H);
  gradient.addColorStop(0, fillColor1);
  gradient.addColorStop(1, fillColor2);

  // Fill area under line
  ctx.beginPath();
  ctx.moveTo(0, H - (data[0]! / 100) * H);
  for (let i = 1; i < data.length; i++) {
    ctx.lineTo(i * step, H - (data[i]! / 100) * H);
  }
  ctx.lineTo(W, H);
  ctx.lineTo(0, H);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Stroke line
  ctx.beginPath();
  ctx.moveTo(0, H - (data[0]! / 100) * H);
  for (let i = 1; i < data.length; i++) {
    ctx.lineTo(i * step, H - (data[i]! / 100) * H);
  }
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 2;
  ctx.shadowColor = strokeColor;
  ctx.shadowBlur = 4;
  ctx.stroke();
  ctx.shadowBlur = 0;

  // End dot
  const lastX = (data.length - 1) * step;
  const lastY = H - (data[data.length - 1]! / 100) * H;
  ctx.beginPath();
  ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
  ctx.fillStyle = strokeColor;
  ctx.shadowColor = strokeColor;
  ctx.shadowBlur = 8;
  ctx.fill();
  ctx.shadowBlur = 0;
}
