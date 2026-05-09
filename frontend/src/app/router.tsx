import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoadingPulse } from '@/components/ui/LoadingPulse';

const GpuPage       = lazy(() => import('@/features/gpu/GpuStatusPanel').then(m => ({ default: m.GpuStatusPanel })));
const ChatPage      = lazy(() => import('@/features/chat/ChatPanel').then(m => ({ default: m.ChatPanel })));
const ProvidersPage = lazy(() => import('@/features/providers/ProvidersPage').then(m => ({ default: m.ProvidersPage })));
const ModelsPage    = lazy(() => import('@/features/models/ModelsPage').then(m => ({ default: m.ModelsPage })));

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

      <Route path="/chat" element={
        <SuspensePage>
          <ChatPage />
        </SuspensePage>
      } />
      <Route path="/voice"            element={<Placeholder name="Voice" />} />
      <Route path="/vision"           element={<Placeholder name="Vision" />} />
      <Route path="/memory"           element={<Placeholder name="Memory" />} />
      <Route path="/tools"            element={<Placeholder name="Tools" />} />
      <Route path="/execution"        element={<Placeholder name="Execution Sandbox" />} />
      <Route path="/search"           element={<Placeholder name="Search" />} />
      <Route path="/terminal"         element={<Placeholder name="Terminal" />} />
      <Route path="/providers" element={
        <SuspensePage>
          <div className="h-full overflow-auto">
            <ProvidersPage />
          </div>
        </SuspensePage>
      } />
      <Route path="/models" element={
        <SuspensePage>
          <div className="h-full overflow-auto">
            <ModelsPage />
          </div>
        </SuspensePage>
      } />
      <Route path="/monitoring"       element={<Placeholder name="Monitoring" />} />
      <Route path="/local-actions"    element={<Placeholder name="Local Actions" />} />
      <Route path="/self-improvement" element={<Placeholder name="Self-Improvement" />} />
      <Route path="/settings"         element={<Placeholder name="Settings" />} />

      <Route path="*" element={<Placeholder name="404 — Page Not Found" />} />
    </Routes>
  );
}
