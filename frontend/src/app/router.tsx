import React, { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoadingPulse } from '@/components/ui/LoadingPulse';

const GpuPage              = lazy(() => import('@/features/gpu/GpuStatusPanel').then(m => ({ default: m.GpuStatusPanel })));
const ChatPage             = lazy(() => import('@/features/chat/ChatPanel').then(m => ({ default: m.ChatPanel })));
const DashboardPage        = lazy(() => import('@/features/dashboard/DashboardPage').then(m => ({ default: m.DashboardPage })));
const ProvidersPage        = lazy(() => import('@/features/providers/ProvidersPage').then(m => ({ default: m.ProvidersPage })));
const ModelsPage           = lazy(() => import('@/features/models/ModelsPage').then(m => ({ default: m.ModelsPage })));
const VoicePage            = lazy(() => import('@/features/voice/VoicePanel').then(m => ({ default: m.VoicePanel })));
const MemoryPage           = lazy(() => import('@/features/memory/MemoryPanel').then(m => ({ default: m.MemoryPanel })));
const TerminalPage         = lazy(() => import('@/features/execution/TerminalPanel').then(m => ({ default: m.TerminalPanel })));
const ToolsPage            = lazy(() => import('@/features/tools/ToolsPanel').then(m => ({ default: m.ToolsPanel })));
const SettingsPage         = lazy(() => import('@/features/settings/SettingsPage').then(m => ({ default: m.SettingsPage })));
const SearchPage           = lazy(() => import('@/features/search/SearchPanel').then(m => ({ default: m.SearchPanel })));
const VisionPage           = lazy(() => import('@/features/vision/VisionPanel').then(m => ({ default: m.VisionPanel })));
const MonitoringPage       = lazy(() => import('@/features/monitoring/MonitoringPage').then(m => ({ default: m.MonitoringPage })));
const SelfImprovementPage  = lazy(() => import('@/features/selfImprovement/SelfImprovementPage').then(m => ({ default: m.SelfImprovementPage })));
const LocalActionsPage     = lazy(() => import('@/features/localActions/LocalActionsPage').then(m => ({ default: m.LocalActionsPage })));

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
      <Route path="/" element={<SuspensePage><div className="h-full overflow-auto"><DashboardPage /></div></SuspensePage>} />
      <Route path="/dashboard" element={<Navigate to="/" replace />} />

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
      <Route path="/voice" element={<SuspensePage><div className="h-full overflow-auto"><VoicePage /></div></SuspensePage>} />
      <Route path="/vision" element={<SuspensePage><div className="h-full overflow-auto"><VisionPage /></div></SuspensePage>} />
      <Route path="/memory" element={<SuspensePage><div className="h-full overflow-auto"><MemoryPage /></div></SuspensePage>} />
      <Route path="/tools" element={<SuspensePage><div className="h-full overflow-auto"><ToolsPage /></div></SuspensePage>} />
      <Route path="/execution" element={<SuspensePage><TerminalPage /></SuspensePage>} />
      <Route path="/search" element={<SuspensePage><div className="h-full overflow-auto"><SearchPage /></div></SuspensePage>} />
      <Route path="/terminal" element={<SuspensePage><TerminalPage /></SuspensePage>} />
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
      <Route path="/monitoring" element={<SuspensePage><div className="h-full overflow-auto"><MonitoringPage /></div></SuspensePage>} />
      <Route path="/local-actions" element={<SuspensePage><div className="h-full overflow-auto"><LocalActionsPage /></div></SuspensePage>} />
      <Route path="/self-improvement" element={<SuspensePage><div className="h-full overflow-auto"><SelfImprovementPage /></div></SuspensePage>} />
      <Route path="/settings" element={<SuspensePage><div className="h-full overflow-auto"><SettingsPage /></div></SuspensePage>} />

      <Route path="*" element={<Placeholder name="404 — Page Not Found" />} />
    </Routes>
  );
}
