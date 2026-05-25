import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { useSwarmStatus, useSwarms, useSwarmDetail, useSwarmHealth, useCreateSwarm, useDeleteSwarm, useAutoScale, useHealSwarms } from './useSwarmManager';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { StatusDot } from '@/components/ui/StatusDot';
import { Users, Plus, Trash2, HeartPulse, Scale, ChevronDown, ChevronRight, AlertTriangle, Layers } from 'lucide-react';

export function SwarmManagerPanel() {
  const [expandedSwarm, setExpandedSwarm] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createRole, setCreateRole] = useState('general');
  const [createMin, setCreateMin] = useState(1);
  const [createMax, setCreateMax] = useState(3);

  const { data: status } = useSwarmStatus();
  const { data: swarmsData } = useSwarms();
  const { data: healthData } = useSwarmHealth();
  const { data: swarmDetail } = useSwarmDetail(expandedSwarm);

  const createSwarm = useCreateSwarm();
  const deleteSwarm = useDeleteSwarm();
  const autoScale = useAutoScale();
  const healSwarms = useHealSwarms();

  const swarms = swarmsData?.swarms ?? [];
  const healthReports = healthData?.health ?? [];
  const healthyCount = healthReports.filter(h => h.isHealthy).length;
  const degradedCount = healthReports.filter(h => !h.isHealthy).length;

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <SectionHeader
            title="Swarm Manager"
            subtitle="Distributed autonomous agent intelligence"
            icon={Layers}
          />
        </div>
        <div className="flex items-center gap-3">
          <NeonBadge color="cyan" label={`${status?.totalSwarms ?? 0} Swarms`} size="sm" />
          <NeonBadge color="green" label={`${status?.activeAgents ?? 0} Agents`} size="sm" />
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex items-center gap-3">
        <CockpitButton icon={<Plus size={14} />} onClick={() => setShowCreate(!showCreate)} variant="primary" size="sm">New Swarm</CockpitButton>
        <CockpitButton icon={<Scale size={14} />} onClick={() => autoScale.mutate()} variant="ghost" size="sm" loading={autoScale.isPending}>Auto-Scale</CockpitButton>
        <CockpitButton icon={<HeartPulse size={14} />} onClick={() => healSwarms.mutate()} variant="ghost" size="sm" loading={healSwarms.isPending}>Heal All</CockpitButton>
      </div>

      {/* Create form */}
      <AnimatePresence>
        {showCreate && (
          <m.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <GlassPanel className="p-4 space-y-3">
              <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider">Spawn New Swarm</p>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Role</label>
                  <select
                    value={createRole}
                    onChange={(e) => setCreateRole(e.target.value)}
                    className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
                  >
                    {['general','research','coding','planner','security','browser','devops','vision','voice'].map(r => (
                      <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Min Agents</label>
                  <input type="number" min={1} max={10} value={createMin}
                    onChange={(e) => setCreateMin(Number(e.target.value))}
                    className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Max Agents</label>
                  <input type="number" min={1} max={20} value={createMax}
                    onChange={(e) => setCreateMax(Number(e.target.value))}
                    className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <CockpitButton
                  icon={<Plus size={14} />}
                  onClick={() => { createSwarm.mutate({ role: createRole, minAgents: createMin, maxAgents: createMax }); setShowCreate(false); }}
                  size="sm"
                  loading={createSwarm.isPending}
                >Spawn</CockpitButton>
              </div>
            </GlassPanel>
          </m.div>
        )}
      </AnimatePresence>

      {/* Health summary */}
      {healthReports.length > 0 && (
        <GlassPanel className="p-4">
          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="text-jarvis-text-dim">Swarm Health</span>
            <span className="text-jarvis-green">{healthyCount} healthy</span>
            {degradedCount > 0 && <span className="text-jarvis-red">{degradedCount} degraded</span>}
            <div className="flex-1" />
            <span className="text-jarvis-text-dim/60">{healthReports.length} total</span>
          </div>
        </GlassPanel>
      )}

      {/* Swarm list */}
      <div className="space-y-3">
        {swarms.length === 0 && (
          <GlassPanel className="p-8 flex flex-col items-center justify-center gap-3">
            <Users size={32} className="text-jarvis-text-dim/30" />
            <p className="text-jarvis-text-dim text-xs font-mono">No swarms deployed</p>
            <CockpitButton icon={<Plus size={14} />} onClick={() => setShowCreate(true)} size="sm" variant="primary">Create Swarm</CockpitButton>
          </GlassPanel>
        )}

        {swarms.map((swarm) => {
          const health = healthReports.find(h => h.swarmId === swarm.swarmId);
          const isExpanded = expandedSwarm === swarm.swarmId;
          return (
            <GlassPanel key={swarm.swarmId} className="overflow-hidden">
              {/* Summary row */}
              <button
                onClick={() => setExpandedSwarm(isExpanded ? null : swarm.swarmId)}
                className="w-full flex items-center gap-3 p-4 hover:bg-jarvis-bg-2/30 transition-colors cursor-pointer text-left"
              >
                <StatusDot status={health?.isHealthy ? 'active' : 'inactive'} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-jarvis-text-bright capitalize">{swarm.role} Swarm</p>
                  <p className="text-[10px] font-mono text-jarvis-text-dim/60 truncate">{swarm.swarmId}</p>
                </div>
                <div className="flex items-center gap-3">
                  <NeonBadge color={health?.isHealthy ? 'green' : 'red'} label={health?.isHealthy ? 'Healthy' : 'Degraded'} size="sm" />
                  <span className="text-xs font-mono text-jarvis-text-dim/80">{swarm.agentCount} agents</span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteSwarm.mutate(swarm.swarmId); }}
                  className="p-1.5 rounded-lg hover:bg-jarvis-red/10 text-jarvis-text-dim/40 hover:text-jarvis-red transition-colors"
                  title="Terminate swarm"
                >
                  <Trash2 size={14} />
                </button>
                <div className="text-jarvis-text-dim/30">
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </div>
              </button>

              {/* Expanded detail */}
              <AnimatePresence>
                {isExpanded && swarmDetail && (
                  <m.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden border-t border-jarvis-border/20"
                  >
                    <div className="p-4 space-y-4">
                      {/* Spec */}
                      <div className="grid grid-cols-3 gap-3">
                        <div className="p-2 rounded-lg bg-jarvis-bg-2/40">
                          <p className="text-[10px] font-mono text-jarvis-text-dim/60">Min/Max Agents</p>
                          <p className="text-xs font-mono text-jarvis-text-bright mt-0.5">{swarmDetail.spec.minAgents} / {swarmDetail.spec.maxAgents}</p>
                        </div>
                        <div className="p-2 rounded-lg bg-jarvis-bg-2/40">
                          <p className="text-[10px] font-mono text-jarvis-text-dim/60">Priority</p>
                          <p className="text-xs font-mono text-jarvis-text-bright mt-0.5 capitalize">{swarmDetail.spec.priority}</p>
                        </div>
                        <div className="p-2 rounded-lg bg-jarvis-bg-2/40">
                          <p className="text-[10px] font-mono text-jarvis-text-dim/60">Concurrent Tasks</p>
                          <p className="text-xs font-mono text-jarvis-text-bright mt-0.5">{swarmDetail.spec.maxConcurrentTasks}</p>
                        </div>
                      </div>

                      {/* Metrics (if available) */}
                      {swarmDetail.metrics && (
                        <div>
                          <p className="text-[10px] font-mono text-jarvis-text-dim/60 mb-2 uppercase tracking-wider">Metrics</p>
                          <div className="grid grid-cols-4 gap-3">
                            <div>
                              <p className="text-[10px] font-mono text-jarvis-text-dim/60">Success Rate</p>
                              <p className="text-xs font-mono text-jarvis-green">{(swarmDetail.metrics.avgSuccessRate * 100).toFixed(0)}%</p>
                            </div>
                            <div>
                              <p className="text-[10px] font-mono text-jarvis-text-dim/60">Avg Latency</p>
                              <p className="text-xs font-mono text-jarvis-cyan">{swarmDetail.metrics.avgLatencyMs.toFixed(0)}ms</p>
                            </div>
                            <div>
                              <p className="text-[10px] font-mono text-jarvis-text-dim/60">Utilization</p>
                              <p className="text-xs font-mono text-jarvis-yellow">{swarmDetail.metrics.utilizationPct.toFixed(0)}%</p>
                            </div>
                            <div>
                              <p className="text-[10px] font-mono text-jarvis-text-dim/60">Tasks</p>
                              <p className="text-xs font-mono text-jarvis-text-bright">{swarmDetail.metrics.totalTasksCompleted} ✓</p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Issues */}
                      {health && health.issues.length > 0 && (
                        <div className="p-3 rounded-lg bg-jarvis-red/5 border border-jarvis-red/20">
                          <p className="text-jarvis-red text-[10px] font-mono flex items-center gap-1.5 mb-1">
                            <AlertTriangle size={12} /> Issues
                          </p>
                          {health.issues.map((issue, i) => (
                            <p key={i} className="text-jarvis-text-dim text-[10px] font-mono ml-4">{issue}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  </m.div>
                )}
              </AnimatePresence>
            </GlassPanel>
          );
        })}
      </div>
    </div>
  );
}
