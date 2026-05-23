import { useEffect, useState } from 'react';
import { m } from 'framer-motion';

interface HudVisualizationProps {
  className?: string;
  size?: number;
}

export function HudVisualization({ className = '', size = 260 }: HudVisualizationProps) {
  const [angle, setAngle] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setAngle((prev) => (prev + 1) % 360);
    }, 50);
    return () => clearInterval(id);
  }, []);

  const cx = size / 2;
  const cy = size / 2;
  const outerR = size * 0.45;
  const midR = size * 0.34;
  const innerR = size * 0.22;
  const coreR = size * 0.07;

  // Radar sweep line
  const rad = (angle * Math.PI) / 180;
  const sweepX = cx + outerR * Math.cos(rad);
  const sweepY = cy + outerR * Math.sin(rad);

  return (
    <div className={`relative ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="absolute inset-0">
        <defs>
          <linearGradient id="hudCyan" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#00E5FF" />
            <stop offset="100%" stopColor="#009DFF" />
          </linearGradient>
          <filter id="hudGlow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <radialGradient id="radarSweep">
            <stop offset="0%" stopColor="rgba(0,229,255,0.15)" />
            <stop offset="100%" stopColor="rgba(0,229,255,0)" />
          </radialGradient>
        </defs>

        {/* Outer ring */}
        <circle
          cx={cx} cy={cy} r={outerR}
          stroke="url(#hudCyan)"
          strokeWidth="2"
          fill="none"
          filter="url(#hudGlow)"
          opacity={0.8}
        />

        {/* Mid ring (dashed) */}
        <circle
          cx={cx} cy={cy} r={midR}
          stroke="#00E5FF"
          strokeWidth="1.5"
          strokeDasharray="8 8"
          fill="none"
          opacity={0.5}
        />

        {/* Inner ring */}
        <circle
          cx={cx} cy={cy} r={innerR}
          stroke="#00E5FF"
          strokeWidth="1"
          fill="none"
          opacity={0.3}
        />

        {/* Crosshair lines */}
        <line x1={cx} y1={cy - outerR - 10} x2={cx} y2={cy + outerR + 10} stroke="#00E5FF" strokeWidth="0.5" opacity={0.25} />
        <line x1={cx - outerR - 10} y1={cy} x2={cx + outerR + 10} y2={cy} stroke="#00E5FF" strokeWidth="0.5" opacity={0.25} />

        {/* Diagonal lines */}
        <line x1={cx - outerR * 0.7} y1={cy - outerR * 0.7} x2={cx + outerR * 0.7} y2={cy + outerR * 0.7} stroke="#00E5FF" strokeWidth="0.5" opacity={0.15} />
        <line x1={cx + outerR * 0.7} y1={cy - outerR * 0.7} x2={cx - outerR * 0.7} y2={cy + outerR * 0.7} stroke="#00E5FF" strokeWidth="0.5" opacity={0.15} />

        {/* Tick marks on outer ring */}
        {Array.from({ length: 12 }).map((_, i) => {
          const a = (i * 30 * Math.PI) / 180;
          const r1 = outerR + 4;
          const r2 = outerR + 12;
          return (
            <line
              key={`tick-${i}`}
              x1={cx + r1 * Math.cos(a)}
              y1={cy + r1 * Math.sin(a)}
              x2={cx + r2 * Math.cos(a)}
              y2={cy + r2 * Math.sin(a)}
              stroke="#00E5FF"
              strokeWidth="1"
              opacity={0.4}
            />
          );
        })}

        {/* Radar sweep cone */}
        <path
          d={`M${cx},${cy} L${sweepX},${sweepY} A${outerR},${outerR} 0 0,1 ${cx + outerR * Math.cos(rad + Math.PI / 6)},${cy + outerR * Math.sin(rad + Math.PI / 6)} Z`}
          fill="url(#radarSweep)"
          opacity={0.6}
        />

        {/* Radar sweep line */}
        <line x1={cx} y1={cy} x2={sweepX} y2={sweepY} stroke="#00E5FF" strokeWidth="1.5" opacity={0.7} filter="url(#hudGlow)" />

        {/* Core glow */}
        <circle cx={cx} cy={cy} r={coreR} fill="#00E5FF" filter="url(#hudGlow)" opacity={0.9} />
        <circle cx={cx} cy={cy} r={coreR * 0.5} fill="#D8F6FF" />

        {/* Blips (random dots) */}
        <circle cx={cx - 60} cy={cy - 45} r="3" fill="#00FF85" opacity={0.8} filter="url(#hudGlow)" />
        <circle cx={cx + 70} cy={cy + 30} r="2.5" fill="#00E5FF" opacity={0.6} filter="url(#hudGlow)" />
        <circle cx={cx + 30} cy={cy - 75} r="2" fill="#00E5FF" opacity={0.5} />
        <circle cx={cx - 80} cy={cy + 55} r="2" fill="#00FF85" opacity={0.4} />
      </svg>

      {/* Corner brackets */}
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="absolute inset-0 pointer-events-none">
        <path d={`M10,30 L10,10 L30,10`} fill="none" stroke="#00E5FF" strokeWidth="1.5" opacity={0.6} />
        <path d={`M${size-30},10 L${size-10},10 L${size-10},30`} fill="none" stroke="#00E5FF" strokeWidth="1.5" opacity={0.6} />
        <path d={`M10,${size-30} L10,${size-10} L30,${size-10}`} fill="none" stroke="#00E5FF" strokeWidth="1.5" opacity={0.6} />
        <path d={`M${size-30},${size-10} L${size-10},${size-10} L${size-10},${size-30}`} fill="none" stroke="#00E5FF" strokeWidth="1.5" opacity={0.6} />
      </svg>

      {/* Center label */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={{ marginTop: coreR + 28 }}>
        <m.span
          className="text-[10px] font-mono tracking-[0.3em] text-jarvis-cyan/60"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
          J.A.R.V.I.S
        </m.span>
      </div>
    </div>
  );
}
