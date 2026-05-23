import { NavLink } from 'react-router-dom';
import { m } from 'framer-motion';
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

  const isVisible = (item: NavItem): boolean => {
    if (!item.featureKey) return true;
    if (!features) return true;
    return features[item.featureKey] === true;
  };

  return (
    <aside
      className="w-14 flex flex-col border-r overflow-y-auto scrollbar-thin py-3 bg-jarvis-bg/95"
      style={{ borderColor: 'var(--jarvis-border)' }}
    >
      {NAV_ITEMS.filter(isVisible).map((item) => (
        <SidebarItem key={item.path} item={item} />
      ))}
    </aside>
  );
}

function SidebarItem({ item }: { item: NavItem }) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.path}
      title={item.label}
      className="group relative flex flex-col items-center justify-center h-12 w-full transition-all duration-200 ease-out"
    >
      {({ isActive }) => (
        <span className={cn(
          'absolute inset-0 flex flex-col items-center justify-center transition-all duration-200',
          isActive
            ? 'text-jarvis-cyan'
            : 'text-jarvis-text-dim hover:text-jarvis-cyan/80',
        )}>
          {/* Active indicator bar */}
          {isActive && (
            <m.span
              layoutId="sidebar-active"
              className="absolute left-0 top-1.5 bottom-1.5 w-[3px] bg-gradient-to-b from-jarvis-cyan to-jarvis-blue rounded-r-full"
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            />
          )}

          {/* Icon with glow on active */}
          <div className={cn(
            'relative flex items-center justify-center w-7 h-7 rounded-lg transition-all duration-200',
            isActive && 'bg-jarvis-cyan/10'
          )}>
            <Icon
              size={18}
              strokeWidth={isActive ? 2 : 1.5}
              className={cn(
                'transition-all duration-200',
                isActive ? 'drop-shadow-[0_0_6px_rgba(0,212,255,0.5)]' : ''
              )}
            />
            {/* Hover glow */}
            <div className={cn(
              'absolute inset-0 rounded-lg opacity-0 transition-opacity duration-200',
              'group-hover:opacity-100 bg-gradient-to-br from-jarvis-cyan/5 to-transparent'
            )} />
          </div>

          {/* Label */}
          <span className={cn(
            'text-[8px] mt-0.5 font-mono uppercase tracking-[0.1em] transition-all duration-200',
            isActive ? 'text-jarvis-cyan' : 'text-jarvis-text-dim group-hover:text-jarvis-cyan/80'
          )}>
            {item.label}
          </span>

          {/* Tooltip on hover */}
          <div className={cn(
            'absolute left-full ml-3 top-1/2 -translate-y-1/2 z-50',
            'px-2.5 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap',
            'bg-jarvis-bg-3/95 border border-jarvis-border text-jarvis-text',
            'shadow-lg shadow-black/40 backdrop-blur-xl',
            'opacity-0 invisible group-hover:opacity-100 group-hover:visible',
            'transition-all duration-200 translate-x-[-4px] group-hover:translate-x-0',
            'pointer-events-none'
          )}>
            {item.label}
          </div>
        </span>
      )}
    </NavLink>
  );
}
