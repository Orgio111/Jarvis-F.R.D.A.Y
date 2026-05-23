import React from 'react';
import { m } from 'framer-motion';

// ─── Shared skeleton primitives ───────────────────────────────────────────────

function SkeletonBar({ className = '' }: { className?: string }) {
  return (
    <div
      className={`h-2 rounded-full bg-jarvis-border/50 animate-pulse ${className}`}
    />
  );
}

function SkeletonBlock({ className = '', children }: { className?: string; children?: React.ReactNode }) {
  return (
    <div
      className={`rounded-lg bg-jarvis-bg-2/70 border border-jarvis-border/20 animate-pulse ${className}`}
    >
      {children}
    </div>
  );
}

function SkeletonIcon({ className = '' }: { className?: string }) {
  return (
    <div
      className={`w-8 h-8 rounded-lg bg-jarvis-border/40 animate-pulse ${className}`}
    />
  );
}

function SkeletonHeading({ className = '' }: { className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      <SkeletonBar className="h-4 w-48" />
      <SkeletonBar className="h-3 w-32" />
    </div>
  );
}

function SkeletonPanel({ className = '', children }: { className?: string; children?: React.ReactNode }) {
  return (
    <SkeletonBlock className={`p-5 space-y-4 ${className}`}>
      {children ?? (
        <>
          <SkeletonBar className="h-3 w-24" />
          <div className="space-y-2.5">
            <SkeletonBar className="h-2 w-full" />
            <SkeletonBar className="h-2 w-3/4" />
            <SkeletonBar className="h-2 w-5/6" />
          </div>
        </>
      )}
    </SkeletonBlock>
  );
}

function SkeletonMetricCard({ className = '' }: { className?: string }) {
  return (
    <SkeletonBlock className={`p-4 space-y-2 ${className}`}>
      <SkeletonIcon className="w-6 h-6" />
      <SkeletonBar className="h-6 w-16" />
      <SkeletonBar className="h-2 w-20" />
    </SkeletonBlock>
  );
}

function SkeletonUtilBar({ className = '' }: { className?: string }) {
  return (
    <div className={`space-y-1 ${className}`}>
      <div className="flex justify-between">
        <SkeletonBar className="h-2 w-16" />
        <SkeletonBar className="h-2 w-8" />
      </div>
      <div className="h-2 bg-jarvis-border/30 rounded-full overflow-hidden">
        <m.div
          className="h-full rounded-full bg-jarvis-border/50"
          initial={{ width: '20%' }}
          animate={{ width: ['20%', '60%', '35%', '70%', '20%'] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
    </div>
  );
}

// ─── Entry point — maps path -> skeleton ─────────────────────────────────────

export type SkeletonKey =
  | 'dashboard'
  | 'chat'
  | 'gpu'
  | 'voice'
  | 'vision'
  | 'memory'
  | 'tools'
  | 'search'
  | 'terminal'
  | 'providers'
  | 'models'
  | 'monitoring'
  | 'settings'
  | 'selfImprovement'
  | 'localActions';

const SKELETON_MAP: Record<SkeletonKey, () => JSX.Element> = {
  dashboard: DashboardSkeleton,
  chat: ChatSkeleton,
  gpu: GpuSkeleton,
  voice: VoiceSkeleton,
  vision: VisionSkeleton,
  memory: MemorySkeleton,
  tools: ToolsSkeleton,
  search: SearchSkeleton,
  terminal: TerminalSkeleton,
  providers: ProvidersSkeleton,
  models: ModelsSkeleton,
  monitoring: MonitoringSkeleton,
  settings: SettingsSkeleton,
  selfImprovement: SelfImprovementSkeleton,
  localActions: LocalActionsSkeleton,
};

export function PageSkeleton({ page }: { page: SkeletonKey }) {
  const Component = SKELETON_MAP[page] ?? DashboardSkeleton;
  return <Component />;
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <SkeletonHeading />
        <SkeletonBar className="h-6 w-48" />
      </div>

      {/* HUD Row 2-1-2 */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <SkeletonPanel className="lg:col-span-2 h-64" />
        <SkeletonBlock className="lg:col-span-1 h-64 flex items-center justify-center">
          <div className="w-28 h-28 rounded-full border-2 border-jarvis-border/30" />
        </SkeletonBlock>
        <SkeletonPanel className="lg:col-span-2 h-64" />
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => <SkeletonMetricCard key={i} />)}
      </div>

      {/* Tab nav */}
      <SkeletonBlock className="p-3">
        <div className="flex gap-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <SkeletonBar key={i} className="h-8 w-24 rounded-lg" />
          ))}
        </div>
      </SkeletonBlock>

      {/* Quick actions */}
      <div className="grid grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => <SkeletonBlock key={i} className="h-12 rounded-lg" />)}
      </div>

      {/* Features panel */}
      <SkeletonPanel className="h-24" />

      {/* Status bar */}
      <SkeletonBlock className="p-4 h-10" />
    </div>
  );
}

// ─── Chat ─────────────────────────────────────────────────────────────────────

function ChatSkeleton() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-jarvis-border/30 shrink-0">
        <SkeletonIcon className="w-7 h-7" />
        <SkeletonHeading />
      </div>

      {/* Empty state area */}
      <div className="flex-1 flex items-center justify-center px-5">
        <m.div
          className="flex flex-col items-center gap-6"
          initial={{ opacity: 0.5 }}
          animate={{ opacity: [0.5, 0.8, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        >
          <SkeletonBlock className="w-16 h-16 rounded-2xl" />
          <SkeletonBar className="h-4 w-40" />
          <SkeletonBar className="h-3 w-60" />
          <div className="grid grid-cols-2 gap-2 w-80">
            {[0, 1, 2, 3].map((i) => (
              <SkeletonBlock key={i} className="h-10 rounded-xl" />
            ))}
          </div>
        </m.div>
      </div>

      {/* Input area */}
      <div className="px-5 py-3 border-t border-jarvis-border/30 shrink-0">
        <SkeletonBlock className="h-10 rounded-lg" />
      </div>
    </div>
  );
}

// ─── GPU ──────────────────────────────────────────────────────────────────────

function GpuSkeleton() {
  return (
    <div className="p-4 space-y-4 overflow-auto h-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SkeletonIcon className="w-8 h-8 rounded-xl" />
          <SkeletonHeading />
        </div>
        <SkeletonBar className="h-6 w-20 rounded-full" />
      </div>

      <SkeletonPanel className="h-32">
        <div className="grid grid-cols-2 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-jarvis-bg-2/40">
              <SkeletonIcon className="w-6 h-6" />
              <div className="space-y-1">
                <SkeletonBar className="h-2 w-12" />
                <SkeletonBar className="h-3 w-20" />
              </div>
            </div>
          ))}
        </div>
      </SkeletonPanel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SkeletonPanel className="h-40" />
        <SkeletonPanel className="h-40" />
      </div>
    </div>
  );
}

// ─── Voice ────────────────────────────────────────────────────────────────────

function VoiceSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SkeletonPanel className="h-48" />
        <SkeletonPanel className="h-48" />
      </div>
    </div>
  );
}

// ─── Vision ───────────────────────────────────────────────────────────────────

function VisionSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <SkeletonBlock className="p-8 h-64 flex items-center justify-center">
        <SkeletonIcon className="w-12 h-12" />
      </SkeletonBlock>
      <SkeletonPanel className="h-40" />
    </div>
  );
}

// ─── Memory ───────────────────────────────────────────────────────────────────

function MemorySkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <SkeletonBlock className="p-3">
        <SkeletonBar className="h-9 w-full rounded-lg" />
      </SkeletonBlock>
      <div className="space-y-3">
        {[0, 1, 2].map((i) => <SkeletonPanel key={i} className="h-24" />)}
      </div>
    </div>
  );
}

// ─── Tools ────────────────────────────────────────────────────────────────────

function ToolsSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <div className="space-y-3">
        {[0, 1, 2].map((i) => <SkeletonPanel key={i} className="h-20" />)}
      </div>
    </div>
  );
}

// ─── Search ───────────────────────────────────────────────────────────────────

function SearchSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <SkeletonBlock className="p-3">
        <SkeletonBar className="h-9 w-full rounded-lg" />
      </SkeletonBlock>
      <div className="space-y-3">
        {[0, 1, 2, 3].map((i) => (
          <SkeletonBlock key={i} className="p-4 space-y-2">
            <SkeletonBar className="h-3 w-3/4" />
            <SkeletonBar className="h-2 w-full" />
            <SkeletonBar className="h-2 w-5/6" />
            <SkeletonBar className="h-2 w-1/2" />
          </SkeletonBlock>
        ))}
      </div>
    </div>
  );
}

// ─── Terminal ─────────────────────────────────────────────────────────────────

function TerminalSkeleton() {
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-0 shrink-0">
        <SkeletonHeading />
      </div>
      <div className="flex-1 flex min-h-0 p-4 pt-2 gap-3">
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex gap-2">
            {[0, 1].map((i) => <SkeletonBlock key={i} className="h-8 w-20 rounded-lg" />)}
          </div>
          <SkeletonBlock className="flex-none h-52 rounded-lg p-3">
            <div className="space-y-2">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <SkeletonBar key={i} className="h-2 w-full" />
              ))}
            </div>
          </SkeletonBlock>
          <SkeletonBlock className="h-9 w-32 rounded-lg" />
          <SkeletonBlock className="flex-1 rounded-lg p-3">
            <div className="space-y-1">
              <SkeletonBar className="h-2 w-24" />
            </div>
          </SkeletonBlock>
        </div>
        {/* Suggestions sidebar placeholder */}
        <SkeletonBlock className="w-[260px] shrink-0 rounded-none border-l border-jarvis-border/30">
          <div className="p-3 space-y-2">
            {[0, 1, 2].map((i) => <SkeletonBar key={i} className="h-16 w-full rounded-lg" />)}
          </div>
        </SkeletonBlock>
      </div>
    </div>
  );
}

// ─── Providers ────────────────────────────────────────────────────────────────

function ProvidersSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        {[0, 1].map((i) => <SkeletonPanel key={i} className="h-40" />)}
      </div>
    </div>
  );
}

// ─── Models ───────────────────────────────────────────────────────────────────

function ModelsSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <SkeletonBlock className="p-3 max-w-sm">
        <SkeletonBar className="h-9 w-full rounded-lg" />
      </SkeletonBlock>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <SkeletonBlock key={i} className="p-4 space-y-3">
            <div className="flex justify-between">
              <div className="space-y-1">
                <SkeletonBar className="h-3 w-28" />
                <SkeletonBar className="h-2 w-20" />
              </div>
              <SkeletonBar className="h-4 w-10 rounded" />
            </div>
            <div className="flex gap-1">
              <SkeletonBar className="h-4 w-12 rounded" />
              <SkeletonBar className="h-4 w-14 rounded" />
            </div>
            <SkeletonBar className="h-2 w-full" />
            <SkeletonBar className="h-2 w-3/4" />
          </SkeletonBlock>
        ))}
      </div>
    </div>
  );
}

// ─── Monitoring ───────────────────────────────────────────────────────────────

function MonitoringSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[0, 1].map((i) => (
          <SkeletonBlock key={i} className="p-5 space-y-4">
            <SkeletonBar className="h-4 w-16" />
            {[0, 1, 2].map((j) => <SkeletonUtilBar key={j} />)}
          </SkeletonBlock>
        ))}
      </div>
    </div>
  );
}

// ─── Settings ─────────────────────────────────────────────────────────────────

function SettingsSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <SkeletonBlock key={i} className="p-5 space-y-3">
            <SkeletonBar className="h-4 w-20" />
            {[0, 1, 2, 3, 4].map((j) => (
              <div key={j} className="flex gap-2">
                <SkeletonBar className="h-3 w-28" />
                <SkeletonBar className="h-3 w-20" />
              </div>
            ))}
          </SkeletonBlock>
        ))}
      </div>
    </div>
  );
}

// ─── Self-Improvement ─────────────────────────────────────────────────────────

function SelfImprovementSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      {/* Status bar */}
      <SkeletonBlock className="p-4 h-12" />
      {/* Textarea */}
      <SkeletonBlock className="p-5 space-y-3">
        <SkeletonBar className="h-4 w-32" />
        <SkeletonBlock className="h-24 w-full" />
        <SkeletonBar className="h-9 w-40 rounded-lg" />
      </SkeletonBlock>
      {/* Suggestions list */}
      <div className="space-y-3">
        {[0, 1].map((i) => <SkeletonPanel key={i} className="h-24" />)}
      </div>
    </div>
  );
}

// ─── Local Actions ────────────────────────────────────────────────────────────

function LocalActionsSkeleton() {
  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      <SkeletonHeading />
      <SkeletonBlock className="p-4 h-12" />
      <div className="flex gap-4">
        {/* Sidebar */}
        <div className="w-56 shrink-0 space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <SkeletonBlock key={i} className="p-3 space-y-2 h-20" />
          ))}
        </div>
        {/* Main panel */}
        <div className="flex-1">
          <SkeletonPanel className="h-48" />
        </div>
      </div>
    </div>
  );
}
