import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { m, AnimatePresence } from 'framer-motion';
import {
  Home,
  MessageSquare,
  Mic,
  Camera,
  Database,
  Wrench,
  PlayCircle,
  Search,
  Terminal,
  Cpu,
  Cable,
  Boxes,
  Activity,
  Zap,
  RefreshCw,
  Settings,
  ChevronLeft,
  Menu,
  Code2,
  Workflow,
  Monitor,
  Brain,
  Radio,
  Image,
  Dna,
  Globe,
  Users,
  Layers,
  FlaskConical,
  GitBranch,
  Store,
  Network,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import type { LucideIcon } from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  featureKey?: keyof import('@/lib/api/types').FeatureFlags;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/',               label: 'Dashboard',     icon: Home },
  { path: '/chat',           label: 'Chat',          icon: MessageSquare, featureKey: 'chat' },
  { path: '/voice',          label: 'Voice',         icon: Mic, featureKey: 'voice' },
  { path: '/vision',         label: 'Vision',        icon: Camera, featureKey: 'vision' },
  { path: '/memory',         label: 'Memory',        icon: Database, featureKey: 'memory' },
  { path: '/tools',          label: 'Tools',         icon: Wrench, featureKey: 'tools' },
  { path: '/execution',      label: 'Execution',     icon: PlayCircle, featureKey: 'execution' },
  { path: '/search',         label: 'Search',        icon: Search, featureKey: 'search' },
  { path: '/code-index',        label: 'Code Intel',     icon: Code2 },
  { path: '/workflows',         label: 'Workflows',      icon: Workflow },
  { path: '/device-agent',      label: 'Device Agent',   icon: Monitor },
  { path: '/reasoning',         label: 'Reasoning',      icon: Brain },
  { path: '/provider-discovery', label: 'Discovery',    icon: Radio },
  { path: '/image-generation',  label: 'Images',         icon: Image },
  { path: '/prompt-mutation',   label: 'Prompts',        icon: Dna },
  { path: '/external-apis',     label: 'APIs',           icon: Globe },
  { path: '/swarm',             label: 'Swarm',          icon: Users },
  { path: '/multi-agent',       label: 'Multi-Agent',    icon: Network },
  { path: '/memory-fabric',     label: 'Memory Fab',     icon: Layers },
  { path: '/self-evolution',    label: 'Evolution',     icon: FlaskConical },
  { path: '/agent-run',         label: 'Agent Run',     icon: GitBranch },
  { path: '/skills',            label: 'Skill OS',      icon: Store },
  { path: '/terminal',       label: 'Terminal',      icon: Terminal, featureKey: 'terminal' },
  { path: '/gpu',            label: 'GPU',           icon: Cpu, featureKey: 'gpuMonitor' },
  { path: '/providers',      label: 'Providers',     icon: Cable },
  { path: '/models',         label: 'Models',        icon: Boxes },
  { path: '/monitoring',     label: 'Monitor',       icon: Activity },
  { path: '/local-actions',  label: 'Actions',       icon: Zap, featureKey: 'localControl' },
  { path: '/self-improvement', label: 'Self-Improve', icon: RefreshCw, featureKey: 'selfImprovement' },
  { path: '/settings',       label: 'Settings',      icon: Settings },
];

export function Sidebar() {
  const features = useBootstrapStore((s) => s.data?.features);
  const [expanded, setExpanded] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Auto-collapse on smaller screens
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 1023px)');
    const handler = (e: MediaQueryListEvent | MediaQueryList) => {
      setExpanded(!e.matches);
    };
    handler(mq);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const isVisible = (item: NavItem): boolean => {
    if (!item.featureKey) return true;
    if (!features) return true;
    return features[item.featureKey] === true;
  };

  const visibleItems = NAV_ITEMS.filter(isVisible);

  const sidebarNav = (
    <>
      {visibleItems.map((item) => (
        <SidebarItem key={item.path} item={item} expanded={expanded} />
      ))}
    </>
  );

  return (
    <>
      {/* ── Desktop sidebar ── */}
      <m.aside
        className="hidden sm:flex flex-col border-r overflow-y-auto scrollbar-thin bg-jarvis-bg/95 shrink-0 z-20"
        style={{ borderColor: 'var(--jarvis-border)' }}
        animate={{ width: expanded ? 192 : 56 }}
        transition={{ type: 'spring', stiffness: 280, damping: 28 }}
      >
        {/* Toggle button */}
        <div className="flex items-center justify-end h-9 px-2 border-b border-jarvis-border/20 shrink-0">
          {expanded && (
            <span className="text-[9px] font-mono text-jarvis-text-dim/30 tracking-[0.2em] uppercase mr-auto">
              NAV
            </span>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-5 h-5 flex items-center justify-center rounded text-jarvis-text-dim/30 hover:text-jarvis-cyan hover:bg-jarvis-cyan/5 transition-all duration-200"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            <m.div
              animate={{ rotate: expanded ? 0 : 180 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
            >
              <ChevronLeft size={12} />
            </m.div>
          </button>
        </div>

        {sidebarNav}
      </m.aside>

      {/* ── Mobile hamburger button ── */}
      <button
        onClick={() => setMobileOpen(true)}
        className="sm:hidden fixed top-[18px] left-3 z-30 w-7 h-7 flex items-center justify-center rounded-lg bg-jarvis-bg-2/90 border border-jarvis-border/50 text-jarvis-text-dim/60 hover:text-jarvis-cyan hover:border-jarvis-cyan/30 transition-all duration-200"
        aria-label="Open navigation"
      >
        <Menu size={14} />
      </button>

      {/* ── Mobile overlay drawer ── */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <m.div
              key="sidebar-backdrop"
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm sm:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setMobileOpen(false)}
            />

            {/* Drawer */}
            <m.aside
              key="sidebar-drawer"
              className="fixed left-0 top-0 bottom-0 z-50 flex flex-col border-r bg-jarvis-bg/98 backdrop-blur-xl sm:hidden"
              style={{ borderColor: 'var(--jarvis-border)', width: 220 }}
              initial={{ x: -220 }}
              animate={{ x: 0 }}
              exit={{ x: -220 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
              {/* Drawer header */}
              <div className="flex items-center justify-between h-14 px-4 border-b border-jarvis-border/20 shrink-0">
                <span className="text-jarvis-cyan text-sm font-bold tracking-[0.15em]">J.A.R.V.I.S</span>
                <button
                  onClick={() => setMobileOpen(false)}
                  className="w-7 h-7 flex items-center justify-center rounded text-jarvis-text-dim/40 hover:text-jarvis-cyan hover:bg-jarvis-cyan/5 transition-all"
                >
                  <ChevronLeft size={16} />
                </button>
              </div>

              {/* Nav items */}
              <div className="flex-1 overflow-y-auto scrollbar-thin py-2">
                {visibleItems.map((item) => (
                  <MobileNavItem key={item.path} item={item} onNavigate={() => setMobileOpen(false)} />
                ))}
              </div>
            </m.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

// ─── Sidebar Item (desktop) ──────────────────────────────────────────────────

function SidebarItem({ item, expanded }: { item: NavItem; expanded: boolean }) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.path}
      title={!expanded ? item.label : undefined}
      className="group relative flex items-center h-11 w-full"
    >
      {({ isActive }) => (
        <span
          className={cn(
            'absolute inset-0 flex items-center transition-all duration-200',
            expanded ? 'px-3 gap-3' : 'justify-center',
            isActive
              ? 'text-jarvis-cyan'
              : 'text-jarvis-text-dim hover:text-jarvis-cyan/80',
          )}
        >
          {/* Background highlight on hover */}
          <m.div
            className={cn(
              'absolute inset-x-2 inset-y-0 rounded-lg opacity-0 transition-opacity duration-200 bg-gradient-to-r from-jarvis-cyan/[0.03] to-transparent',
              'group-hover:opacity-100',
            )}
            initial={false}
          />

          {/* Active indicator */}
          {isActive && (
            <m.span
              layoutId="sidebar-active"
              className="absolute left-0 top-2 bottom-2 w-[3px] bg-gradient-to-b from-jarvis-cyan to-jarvis-blue rounded-r-full"
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            />
          )}

          {/* Icon */}
          <m.div
            className={cn(
              'relative flex items-center justify-center w-7 h-7 rounded-lg shrink-0',
              isActive && 'bg-jarvis-cyan/10',
            )}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
          >
            <Icon
              size={18}
              strokeWidth={isActive ? 2 : 1.5}
              className={cn(
                'transition-all duration-200',
                isActive ? 'drop-shadow-[0_0_6px_rgba(0,212,255,0.5)]' : '',
              )}
            />
            {/* Hover glow */}
            <div
              className={cn(
                'absolute inset-0 rounded-lg opacity-0 transition-all duration-300',
                'group-hover:opacity-100 bg-gradient-to-br from-jarvis-cyan/10 to-transparent',
                isActive && 'opacity-100',
              )}
            />
          </m.div>

          {/* Label (only when expanded) */}
          {expanded && (
            <m.span
              className="text-xs font-mono tracking-[0.05em] truncate"
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -6 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
            >
              {item.label}
            </m.span>
          )}

          {/* Tooltip when collapsed */}
          {!expanded && (
            <m.div
              className={cn(
                'absolute left-full ml-3 top-1/2 -translate-y-1/2 z-50',
                'px-2.5 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap',
                'bg-jarvis-bg-3/95 border border-jarvis-border/50 text-jarvis-text',
                'shadow-lg shadow-black/40 backdrop-blur-xl',
                'opacity-0 invisible group-hover:opacity-100 group-hover:visible',
                'transition-all duration-200 translate-x-[-4px] group-hover:translate-x-0',
                'pointer-events-none',
              )}
            >
              {item.label}
            </m.div>
          )}
        </span>
      )}
    </NavLink>
  );
}

// ─── Mobile Nav Item ─────────────────────────────────────────────────────────

function MobileNavItem({ item, onNavigate }: { item: NavItem; onNavigate: () => void }) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.path}
      onClick={onNavigate}
      className="group relative flex items-center h-11 w-full"
    >
      {({ isActive }) => (
        <span
          className={cn(
            'absolute inset-0 flex items-center gap-3 px-4 transition-all duration-200',
            isActive
              ? 'text-jarvis-cyan'
              : 'text-jarvis-text-dim hover:text-jarvis-cyan/80',
          )}
        >
          {/* Active indicator */}
          {isActive && (
            <m.span
              layoutId="mobile-sidebar-active"
              className="absolute left-0 top-2 bottom-2 w-[3px] bg-gradient-to-b from-jarvis-cyan to-jarvis-blue rounded-r-full"
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            />
          )}

          {/* Icon */}
          <div
            className={cn(
              'flex items-center justify-center w-7 h-7 rounded-lg shrink-0',
              isActive && 'bg-jarvis-cyan/10',
            )}
          >
            <Icon
              size={18}
              strokeWidth={isActive ? 2 : 1.5}
              className={cn(
                isActive ? 'drop-shadow-[0_0_6px_rgba(0,212,255,0.5)]' : '',
              )}
            />
          </div>

          {/* Label */}
          <span
            className={cn(
              'text-sm font-mono tracking-[0.05em]',
              isActive ? 'text-jarvis-cyan' : 'text-jarvis-text-dim group-hover:text-jarvis-cyan/80',
            )}
          >
            {item.label}
          </span>
        </span>
      )}
    </NavLink>
  );
}
