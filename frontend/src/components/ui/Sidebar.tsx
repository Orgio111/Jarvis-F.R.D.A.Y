import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  featureKey?: keyof import('@/lib/api/types').FeatureFlags;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/chat',             label: 'Chat',           icon: '◈', featureKey: 'chat' },
  { path: '/voice',            label: 'Voice',          icon: '◉', featureKey: 'voice' },
  { path: '/vision',           label: 'Vision',         icon: '◎', featureKey: 'vision' },
  { path: '/memory',           label: 'Memory',         icon: '◫', featureKey: 'memory' },
  { path: '/tools',            label: 'Tools',          icon: '◧', featureKey: 'tools' },
  { path: '/execution',        label: 'Execution',      icon: '◩', featureKey: 'execution' },
  { path: '/search',           label: 'Search',         icon: '◌', featureKey: 'search' },
  { path: '/terminal',         label: 'Terminal',       icon: '▸', featureKey: 'terminal' },
  { path: '/gpu',              label: 'GPU',            icon: '◈', featureKey: 'gpuMonitor' },
  { path: '/providers',        label: 'Providers',      icon: '◎' },
  { path: '/models',           label: 'Models',         icon: '◉' },
  { path: '/monitoring',       label: 'Monitor',        icon: '◌' },
  { path: '/local-actions',    label: 'Actions',        icon: '◧', featureKey: 'localControl' },
  { path: '/self-improvement', label: 'Self-Improve',   icon: '◩', featureKey: 'selfImprovement' },
  { path: '/settings',         label: 'Settings',       icon: '◫' },
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
      className="w-14 flex flex-col border-r overflow-y-auto scrollbar-thin py-2"
      style={{ borderColor: 'var(--jarvis-border)', background: 'rgba(8,12,20,0.97)' }}
    >
      {NAV_ITEMS.filter(isVisible).map((item) => (
        <SidebarItem key={item.path} item={item} />
      ))}
    </aside>
  );
}

function SidebarItem({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.path}
      className={({ isActive }) =>
        cn(
          'group relative flex flex-col items-center justify-center h-12 w-full',
          'text-jarvis-text-dim hover:text-jarvis-cyan transition-colors duration-150',
          isActive && 'text-jarvis-cyan',
        )
      }
      title={item.label}
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.div
              className="absolute left-0 top-1 bottom-1 w-0.5 bg-jarvis-cyan rounded-r"
              layoutId="sidebar-indicator"
              transition={{ type: 'spring', stiffness: 400, damping: 35 }}
            />
          )}
          <span className="text-base leading-none">{item.icon}</span>
          <span className="text-[9px] mt-0.5 font-mono uppercase tracking-wide">{item.label}</span>
        </>
      )}
    </NavLink>
  );
}
