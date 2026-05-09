import React from 'react';
import { TopStatusBar } from './TopStatusBar';
import { Sidebar } from './Sidebar';

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * The outermost chrome for the JARVIS cockpit.
 *
 * Layout:
 *   ┌──────────────────── TopStatusBar (h=10) ─────────────────────┐
 *   │ Sidebar (w=14) │  Main workspace  │ (right inspector: TBD)  │
 *   └──────────────────── (full height) ──────────────────────────┘
 */
export function AppShell({ children }: AppShellProps) {
  return (
    <div
      className="flex flex-col w-full h-full overflow-hidden"
      style={{ background: 'var(--jarvis-bg)' }}
    >
      {/* Top bar */}
      <TopStatusBar />

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left navigation */}
        <Sidebar />

        {/* Main workspace */}
        <main className="flex-1 overflow-hidden relative">
          {/* Background grid */}
          <div
            className="absolute inset-0 pointer-events-none opacity-30"
            style={{
              backgroundImage: `
                linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px)
              `,
              backgroundSize: '24px 24px',
            }}
          />
          {/* Radial glow at top */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                'radial-gradient(ellipse at 50% -10%, rgba(0,102,255,0.08) 0%, transparent 60%)',
            }}
          />
          {/* Content */}
          <div className="relative z-10 w-full h-full overflow-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
