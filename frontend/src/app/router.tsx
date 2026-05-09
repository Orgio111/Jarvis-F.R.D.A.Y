import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoadingPulse } from '@/components/ui/LoadingPulse';

const GpuPage       = lazy(() => import('@/features/gpu/GpuStatusPanel').then(m => ({ default: m.GpuStatusPanel })));

function Placeholder({ name }: { name: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div className="jarvis-panel p-8 text-center max-w-sm">
        <p className="text-jarvis-cyan text-sm font-mono mb-2">{name}</p>
        <p className="text-jarvis-text-dim text-xs">Module loading...</p>
      </div>
    </div>
  );
}

function SuspensePage({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full">
          <LoadingPulse label="Loading module..." />
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/chat" replace />} />

      <Route path="/gpu" element={
        <SuspensePage>
          <div className="h-full overflow-auto">
            <GpuPage />
          </div>
        </SuspensePage>
      } />

      {/* Placeholder routes — will be replaced as modules are implemented */}
      <Route path="/chat"             element={<Placeholder name="Chat" />} />
      <Route path="/voice"            element={<Placeholder name="Voice" />} />
      <Route path="/vision"           element={<Placeholder name="Vision" />} />
      <Route path="/memory"           element={<Placeholder name="Memory" />} />
      <Route path="/tools"            element={<Placeholder name="Tools" />} />
      <Route path="/execution"        element={<Placeholder name="Execution Sandbox" />} />
      <Route path="/search"           element={<Placeholder name="Search" />} />
      <Route path="/terminal"         element={<Placeholder name="Terminal" />} />
      <Route path="/providers"        element={<Placeholder name="Providers" />} />
      <Route path="/models"           element={<Placeholder name="Models" />} />
      <Route path="/monitoring"       element={<Placeholder name="Monitoring" />} />
      <Route path="/local-actions"    element={<Placeholder name="Local Actions" />} />
      <Route path="/self-improvement" element={<Placeholder name="Self-Improvement" />} />
      <Route path="/settings"         element={<Placeholder name="Settings" />} />

      <Route path="*" element={<Placeholder name="404 — Page Not Found" />} />
    </Routes>
  );
}
