import React, { lazy, Suspense } from 'react';
import { Link, Routes, Route, Navigate } from 'react-router-dom';
import { m } from 'framer-motion';
import { Home } from 'lucide-react';
import { PageSkeleton } from '@/components/ui/PageSkeletons';
import type { SkeletonKey } from '@/components/ui/PageSkeletons';

const CommunicationPage   = lazy(() => import('@/features/communication/CommunicationPanel').then(m => ({ default: m.CommunicationPanel })));
const DashboardPage        = lazy(() => import('@/features/dashboard/DashboardPage').then(m => ({ default: m.DashboardPage })));
const ToolsPage            = lazy(() => import('@/features/tools/ToolsPanel').then(m => ({ default: m.ToolsPanel })));
const SelfEvolutionPage        = lazy(() => import('@/features/selfEvolution/SelfEvolutionPanel').then(m => ({ default: m.SelfEvolutionPanel })));
const AgentRunPage             = lazy(() => import('@/features/agentRun/AgentRunPanel').then(m => ({ default: m.AgentRunPanel })));
const SkillMarketplacePage     = lazy(() => import('@/features/skillMarketplace/SkillMarketplacePage').then(m => ({ default: m.SkillMarketplacePage })));
const PromptLibraryPage        = lazy(() => import('@/features/promptLibrary/PromptLibraryPage').then(m => ({ default: m.PromptLibraryPage })));
const ObsidianPage             = lazy(() => import('@/features/obsidian/ObsidianPage').then(m => ({ default: m.ObsidianPage })));

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

      <Route path="/chat" element={
        <SuspensePage skeleton="chat">
          <CommunicationPage />
        </SuspensePage>
      } />
      <Route path="/tools" element={<SuspensePage skeleton="tools"><div className="h-full overflow-auto"><ToolsPage /></div></SuspensePage>} />
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
      <Route path="/prompt-library" element={
        <SuspensePage skeleton="search">
          <div className="h-full overflow-auto">
            <PromptLibraryPage />
          </div>
        </SuspensePage>
      } />

      <Route path="/obsidian" element={<SuspensePage skeleton="search"><div className="h-full overflow-auto"><ObsidianPage /></div></SuspensePage>} />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
