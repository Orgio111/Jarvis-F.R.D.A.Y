import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { m } from 'framer-motion';
import { TopStatusBar } from './TopStatusBar';
import { Sidebar } from './Sidebar';
import { RightSidebar } from './RightSidebar';

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * J.A.R.V.I.S HUD Layout:
 *   ┌─────────────────────────── TopStatusBar (h=68px) ────────────────────────────┐
 *   │ Sidebar (w=56px) │  Main workspace          │ RightSidebar (w=280px) │
 *   │                  │  (flex-1)                 │ (dashboard only)       │
 *   └─────────────────────────────────────────────────────────────────────────────┘
 */
export function AppShell({ children }: AppShellProps) {
  const location = useLocation();
  const showRightSidebar = location.pathname === '/';
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="flex flex-col w-full h-full overflow-hidden bg-[#02040A]">
      {/* Top bar */}
      <TopStatusBar />

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left navigation */}
        <Sidebar />

        {/* Main workspace */}
        <main className="flex-1 overflow-hidden relative">
          {/* Background layers */}
          <div className="absolute inset-0 pointer-events-none">
            {/* Grid pattern */}
            <div
              className="absolute inset-0"
              style={{
                backgroundImage: `
                  linear-gradient(rgba(0,212,255,0.025) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(0,212,255,0.025) 1px, transparent 1px)
                `,
                backgroundSize: '40px 40px',
              }}
            />

            {/* Radial glow at top */}
            <div
              className="absolute inset-0"
              style={{
                background: 'radial-gradient(ellipse at 50% -10%, rgba(0,102,255,0.08) 0%, transparent 60%)',
              }}
            />

            {/* Mouse-following glow */}
            <m.div
              className="absolute w-96 h-96 rounded-full pointer-events-none"
              style={{
                background: 'radial-gradient(circle, rgba(0,229,255,0.03) 0%, transparent 60%)',
                left: mousePos.x - 192,
                top: mousePos.y - 192,
              }}
              transition={{ type: 'spring', stiffness: 50, damping: 30 }}
            />
          </div>

          {/* Content */}
          <div className="relative z-10 w-full h-full overflow-auto scrollbar-thin">
            <div className="absolute top-0 left-0 right-0 h-20 bg-gradient-to-b from-jarvis-cyan/[0.02] to-transparent pointer-events-none" />
            <div className="relative">
              {children}
            </div>
          </div>
        </main>

        {/* Right sidebar (dashboard only) */}
        {showRightSidebar && <RightSidebar />}
      </div>
    </div>
  );
}
