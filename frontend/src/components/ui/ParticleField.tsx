import { useEffect, useRef, useCallback } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  life: number;
  maxLife: number;
  color: string;
}

interface ParticleFieldProps {
  count?: number;
  speed?: number;
  className?: string;
}

type RGB = [number, number, number];

const COLORS: RGB[] = [
  [0, 212, 255],   // cyan
  [0, 102, 255],   // blue
  [0, 255, 136],   // green
  [155, 89, 255],  // purple
  [255, 215, 0],   // yellow
];

export function ParticleField({
  count = 40,
  speed = 0.3,
  className = '',
}: ParticleFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animRef = useRef<number>(0);
  const dimsRef = useRef({ w: 0, h: 0 });

  const initParticle = useCallback(
    (w: number, h: number): Particle => {
      const [r, g, b] = COLORS[Math.floor(Math.random() * COLORS.length)];
      const alpha = 0.1 + Math.random() * 0.4;
      return {
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * speed,
        vy: (Math.random() - 0.5) * speed - 0.1,
        size: 1 + Math.random() * 2.5,
        alpha,
        life: 0,
        maxLife: 300 + Math.random() * 400,
        color: `rgba(${r},${g},${b},${alpha})`,
      };
    },
    [speed],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const w = window.innerWidth;
      const h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.scale(dpr, dpr);
      dimsRef.current = { w, h };

      // Reinitialize particles on resize
      particlesRef.current = Array.from({ length: count }, () =>
        initParticle(w, h),
      );
    };

    resize();
    window.addEventListener('resize', resize);

    // Connection distance threshold
    const connectDist = 120;

    const draw = () => {
      const { w, h } = dimsRef.current;
      ctx.clearRect(0, 0, w, h);

      const particles = particlesRef.current;

      // Update and draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.life++;

        // Respawn if dead
        if (p.life > p.maxLife) {
          particles[i] = initParticle(w, h);
          continue;
        }

        // Movement
        p.x += p.vx;
        p.y += p.vy;

        // Wrap around edges with padding
        if (p.x < -20) p.x = w + 20;
        if (p.x > w + 20) p.x = -20;
        if (p.y < -20) p.y = h + 20;
        if (p.y > h + 20) p.y = -20;

        // Fade in/out
        const fadeIn = Math.min(1, p.life / 60);
        const fadeOut = Math.min(1, (p.maxLife - p.life) / 60);
        const currentAlpha = p.alpha * fadeIn * fadeOut;

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color.replace(/[\d.]+$/, String(currentAlpha));
        ctx.fill();

        // Draw connections to nearby particles
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < connectDist) {
            const connAlpha = (1 - dist / connectDist) * currentAlpha * 0.3;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(0, 212, 255, ${connAlpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [count, initParticle]);

  return (
    <canvas
      ref={canvasRef}
      className={`fixed inset-0 pointer-events-none z-0 ${className}`}
      style={{ opacity: 0.6 }}
    />
  );
}
