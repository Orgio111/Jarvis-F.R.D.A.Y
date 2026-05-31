import React, { lazy, Suspense } from 'react';
import { Link, Routes, Route, Navigate } from 'react-router-dom';
import { m } from 'framer-motion';
import { Home } from 'lucide-react';
import { PageSkeleton } from '@/components/ui/PageSkeletons';
import type { SkeletonKey } from '@/components/ui/PageSkeletons';

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
const CodeIndexPage        = lazy(() => import('@/features/codeIndexing/CodeIndexPanel').then(m => ({ default: m.CodeIndexPanel })));
const VisionPage              = lazy(() => import('@/features/vision/VisionPanel').then(m => ({ default: m.VisionPanel })));
const MonitoringPage          = lazy(() => import('@/features/monitoring/MonitoringPage').then(m => ({ default: m.MonitoringPage })));
const SelfImprovementPage     = lazy(() => import('@/features/selfImprovement/SelfImprovementPage').then(m => ({ default: m.SelfImprovementPage })));
const LocalActionsPage        = lazy(() => import('@/features/localActions/LocalActionsPage').then(m => ({ default: m.LocalActionsPage })));
const WorkflowPage            = lazy(() => import('@/features/workflows/WorkflowPanel').then(m => ({ default: m.WorkflowPanel })));
const DeviceAgentPage         = lazy(() => import('@/features/deviceAgent/DeviceAgentPanel').then(m => ({ default: m.DeviceAgentPanel })));
const ReasoningPage           = lazy(() => import('@/features/reasoning/ReasoningPanel').then(m => ({ default: m.ReasoningPanel })));
const ProviderDiscoveryPage   = lazy(() => import('@/features/providerDiscovery/ProviderDiscoveryPanel').then(m => ({ default: m.ProviderDiscoveryPanel })));
const ImageGenerationPage     = lazy(() => import('@/features/imageGeneration/ImageGenerationPanel').then(m => ({ default: m.ImageGenerationPanel })));
const PromptMutationPage      = lazy(() => import('@/features/promptMutation/PromptMutationPanel').then(m => ({ default: m.PromptMutationPanel })));
const ExternalApisPage        = lazy(() => import('@/features/externalApis/ApiRegistryPanel').then(m => ({ default: m.ApiRegistryPanel })));
const SwarmPage                = lazy(() => import('@/features/swarm/SwarmManagerPanel').then(m => ({ default: m.SwarmManagerPanel })));
const MemoryFabricPage         = lazy(() => import('@/features/memoryFabric/MemoryFabricPanel').then(m => ({ default: m.MemoryFabricPanel })));
const SelfEvolutionPage        = lazy(() => import('@/features/selfEvolution/SelfEvolutionPanel').then(m => ({ default: m.SelfEvolutionPanel })));
const AgentRunPage             = lazy(() => import('@/features/agentRun/AgentRunPanel').then(m => ({ default: m.AgentRunPanel })));
const SkillMarketplacePage     = lazy(() => import('@/features/skillMarketplace/SkillMarketplacePage').then(m => ({ default: m.SkillMarketplacePage })));

function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      <m.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="jarvis-panel p-10 text-center max-w-sm relative overflow-hidden"
      >
        {/* Glitch effect */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="jarvis-scanlines absolute inset-0" />
        </div>

        <div className="relative z-10">
          <m.div
            className="w-20 h-20 mx-auto mb-6 flex items-center justify-center rounded-full border-2 border-jarvis-red/40"
            animate={{
              boxShadow: [
                '0 0 20px rgba(255,68,102,0.1)',
                '0 0 40px rgba(255,68,102,0.2)',
                '0 0 20px rgba(255,68,102,0.1)',
              ],
            }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          >
            <span className="text-jarvis-red text-4xl font-mono font-bold">404</span>
          </m.div>

          <p className="text-jarvis-text-bright text-sm font-mono mb-2 tracking-wide">
            Page Not Found
          </p>
          <p className="text-jarvis-text-dim text-xs font-mono leading-relaxed mb-6">
            This sector of the JARVIS system does not exist.
            The navigation coordinates you entered are invalid.
          </p>

          <div className="flex gap-3 justify-center">
            <Link
              to="/"
              className="btn-cockpit-primary px-5 py-2 text-sm flex items-center gap-2"
            >
              <Home size={14} />
              Return to Command Center
            </Link>
          </div>

          <m.div
            className="mt-6 text-[10px] font-mono text-jarvis-text-dim/40"
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          >
            ERROR CODE: NAV_SYS_404 • SIGNAL LOST
          </m.div>
        </div>
      </m.div>
    </div>
  );
}

function SuspensePage({ children, skeleton }: { children: React.ReactNode; skeleton?: SkeletonKey }) {
  return (
    <Suspense
      fallback={
        skeleton ? (
          <PageSkeleton page={skeleton} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-jarvis-text-dim text-xs font-mono animate-pulse">Loading module...</div>
          </div>
        )
      }
    >
      {children}
    </Suspense>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<SuspensePage skeleton="dashboard"><div className="h-full overflow-auto"><DashboardPage /></div></SuspensePage>} />
      <Route path="/dashboard" element={<Navigate to="/" replace />} />

      <Route path="/gpu" element={
        <SuspensePage skeleton="gpu">
          <div className="h-full overflow-auto">
            <GpuPage />
          </div>
        </SuspensePage>
      } />

      <Route path="/chat" element={
        <SuspensePage skeleton="chat">
          <ChatPage />
        </SuspensePage>
      } />
      <Route path="/voice" element={<SuspensePage skeleton="voice"><div className="h-full overflow-auto"><VoicePage /></div></SuspensePage>} />
      <Route path="/vision" element={<SuspensePage skeleton="vision"><div className="h-full overflow-auto"><VisionPage /></div></SuspensePage>} />
      <Route path="/memory" element={<SuspensePage skeleton="memory"><div className="h-full overflow-auto"><MemoryPage /></div></SuspensePage>} />
      <Route path="/tools" element={<SuspensePage skeleton="tools"><div className="h-full overflow-auto"><ToolsPage /></div></SuspensePage>} />
      <Route path="/execution" element={<SuspensePage skeleton="terminal"><TerminalPage /></SuspensePage>} />
      <Route path="/search" element={<SuspensePage skeleton="search"><div className="h-full overflow-auto"><SearchPage /></div></SuspensePage>} />
      <Route path="/code-index" element={<SuspensePage skeleton="search"><div className="h-full overflow-auto"><CodeIndexPage /></div></SuspensePage>} />
      <Route path="/workflows" element={<SuspensePage skeleton="search"><div className="h-full overflow-auto"><WorkflowPage /></div></SuspensePage>} />
      <Route path="/device-agent" element={<SuspensePage skeleton="search"><div className="h-full overflow-auto"><DeviceAgentPage /></div></SuspensePage>} />
      <Route path="/reasoning" element={<SuspensePage skeleton="search"><div className="h-full overflow-auto"><ReasoningPage /></div></SuspensePage>} />
      <Route path="/provider-discovery" element={<SuspensePage skeleton="providers"><div className="h-full overflow-auto"><ProviderDiscoveryPage /></div></SuspensePage>} />
      <Route path="/image-generation" element={<SuspensePage skeleton="search"><div className="h-full overflow-auto"><ImageGenerationPage /></div></SuspensePage>} />
      <Route path="/prompt-mutation" element={<SuspensePage skeleton="search"><div className="h-full overflow-auto"><PromptMutationPage /></div></SuspensePage>} />
      <Route path="/external-apis" element={
        <SuspensePage skeleton="search">
          <div className="h-full overflow-auto">
            <ExternalApisPage />
          </div>
        </SuspensePage>
      } />
      <Route path="/swarm" element={
        <SuspensePage skeleton="search">
          <div className="h-full overflow-auto">
            <SwarmPage />
          </div>
        </SuspensePage>
      } />
      <Route path="/memory-fabric" element={
        <SuspensePage skeleton="search">
          <div className="h-full overflow-auto">
            <MemoryFabricPage />
          </div>
        </SuspensePage>
      } />
      <Route path="/self-evolution" element={
        <SuspensePage skeleton="search">
          <div className="h-full overflow-auto">
            <SelfEvolutionPage />
          </div>
        </SuspensePage>
      } />
      <Route path="/skills" element={
        <SuspensePage skeleton="search">
          <div className="h-full overflow-auto">
            <SkillMarketplacePage />
          </div>
        </SuspensePage>
      } />
      <Route path="/agent-run" element={
        <SuspensePage skeleton="chat">
          <AgentRunPage />
        </SuspensePage>
      } />
      <Route path="/terminal" element={<SuspensePage skeleton="terminal"><TerminalPage /></SuspensePage>} />
      <Route path="/providers" element={
        <SuspensePage skeleton="providers">
          <div className="h-full overflow-auto">
            <ProvidersPage />
          </div>
        </SuspensePage>
      } />
      <Route path="/models" element={
        <SuspensePage skeleton="models">
          <div className="h-full overflow-auto">
            <ModelsPage />
          </div>
        </SuspensePage>
      } />
      <Route path="/monitoring" element={<SuspensePage skeleton="monitoring"><div className="h-full overflow-auto"><MonitoringPage /></div></SuspensePage>} />
      <Route path="/local-actions" element={<SuspensePage skeleton="localActions"><div className="h-full overflow-auto"><LocalActionsPage /></div></SuspensePage>} />
      <Route path="/self-improvement" element={<SuspensePage skeleton="selfImprovement"><div className="h-full overflow-auto"><SelfImprovementPage /></div></SuspensePage>} />
      <Route path="/settings" element={<SuspensePage skeleton="settings"><div className="h-full overflow-auto"><SettingsPage /></div></SuspensePage>} />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
