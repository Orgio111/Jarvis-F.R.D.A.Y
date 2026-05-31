import { useState, useMemo } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import {
  Store, Search, GitFork, TrendingUp, Package, Zap,
  RefreshCw, Filter, Loader2, AlertTriangle, CheckCircle,
} from 'lucide-react';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { SkillCard } from './SkillCard';
import { GitHubImportModal } from './GitHubImportModal';
import { SkillDetailModal } from './SkillDetailModal';
import { useSkillMarketplace } from './useSkillMarketplace';
import type { Skill } from './types';

type Tab = 'all' | 'trending' | 'active' | 'disabled';

const CATEGORIES = ['All', 'Research', 'Coding', 'Data', 'Communication', 'Automation', 'Creative', 'Analysis'];

export function SkillMarketplacePage() {
  const { skills, stats, loading, error, refresh, generateSkill, toggleSkill } = useSkillMarketplace();
  const [tab, setTab] = useState<Tab>('all');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [showGitHubModal, setShowGitHubModal] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [generating, setGenerating] = useState(false);
  const [genPrompt, setGenPrompt] = useState('');
  const [showGenInput, setShowGenInput] = useState(false);
  const [genStatus, setGenStatus] = useState<'idle' | 'ok' | 'err'>('idle');
  const [genMsg, setGenMsg] = useState('');

  const filtered = useMemo(() => {
    return skills.filter((s) => {
      const matchTab =
        tab === 'all' ? true :
        tab === 'trending' ? s.usage_count > 0 :
        tab === 'active' ? s.enabled :
        tab === 'disabled' ? !s.enabled : true;

      const matchSearch = !search || [s.name, s.description, ...(s.tags ?? [])]
        .some((t) => t?.toLowerCase().includes(search.toLowerCase()));

      const matchCat = category === 'All' || s.category === category;

      return matchTab && matchSearch && matchCat;
    });
  }, [skills, tab, search, category]);

  const trending = useMemo(
    () => [...skills].sort((a, b) => b.usage_count - a.usage_count).slice(0, 3),
    [skills],
  );

  const handleGenerate = async () => {
    if (!genPrompt.trim()) return;
    setGenerating(true);
    setGenStatus('idle');
    try {
      const result = await generateSkill(genPrompt.trim());
      if (result?.skill_id) {
        setGenStatus('ok');
        setGenMsg(`Generated: ${result.name}`);
        setGenPrompt('');
        setTimeout(() => { setShowGenInput(false); setGenStatus('idle'); }, 3000);
        refresh();
      } else {
        setGenStatus('err');
        setGenMsg(result?.detail ?? 'Generation failed.');
      }
    } catch (e: any) {
      setGenStatus('err');
      setGenMsg(e?.message ?? 'Network error');
    } finally {
      setGenerating(false);
    }
  };

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'all', label: 'All Skills', count: skills.length },
    { id: 'trending', label: 'Trending', count: skills.filter((s) => s.usage_count > 0).length },
    { id: 'active', label: 'Active', count: skills.filter((s) => s.enabled).length },
    { id: 'disabled', label: 'Disabled', count: skills.filter((s) => !s.enabled).length },
  ];

  return (
    <div className="h-full flex flex-col gap-0 overflow-hidden">
      {/* Top bar */}
      <div className="shrink-0 px-6 pt-5 pb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <SectionHeader
            icon={Store}
            title="Skill OS"
            subtitle="AI capabilities marketplace — browse, import, evolve"
          />
          <div className="flex items-center gap-2 flex-wrap">
            <CockpitButton
              variant="ghost"
              size="sm"
              onClick={refresh}
              icon={<RefreshCw size={12} className={loading ? 'animate-spin' : ''} />}
            >
              Refresh
            </CockpitButton>
            <CockpitButton
              variant="ghost"
              size="sm"
              onClick={() => setShowGitHubModal(true)}
              icon={<GitFork size={12} />}
            >
              GitHub Import
            </CockpitButton>
            <CockpitButton
              variant="primary"
              size="sm"
              onClick={() => setShowGenInput(!showGenInput)}
              icon={<Zap size={12} />}
            >
              Generate Skill
            </CockpitButton>
          </div>
        </div>

        {/* Generate skill input */}
        <AnimatePresence>
          {showGenInput && (
            <m.div
              initial={{ opacity: 0, height: 0, y: -8 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden mt-3"
            >
              <GlassPanel className="p-3">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={genPrompt}
                    onChange={(e) => setGenPrompt(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !generating && handleGenerate()}
                    placeholder="Describe the skill to generate… e.g. 'translate text to Mongolian'"
                    className="flex-1 bg-transparent border-none outline-none text-xs font-mono text-jarvis-text placeholder-jarvis-text-dim/30"
                  />
                  <CockpitButton
                    variant="primary"
                    size="sm"
                    onClick={handleGenerate}
                    disabled={generating || !genPrompt.trim()}
                    icon={generating ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
                  >
                    {generating ? 'Generating…' : 'Generate'}
                  </CockpitButton>
                </div>
                <AnimatePresence>
                  {genStatus !== 'idle' && (
                    <m.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className={`mt-2 flex items-center gap-2 text-[10px] font-mono ${
                        genStatus === 'ok' ? 'text-green-400' : 'text-jarvis-red'
                      }`}
                    >
                      {genStatus === 'ok'
                        ? <CheckCircle size={10} />
                        : <AlertTriangle size={10} />
                      }
                      {genMsg}
                    </m.div>
                  )}
                </AnimatePresence>
              </GlassPanel>
            </m.div>
          )}
        </AnimatePresence>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="shrink-0 px-6 pb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total Skills', value: stats.total_skills, color: 'text-jarvis-cyan' },
            { label: 'Active', value: stats.enabled_skills, color: 'text-green-400' },
            { label: 'Executions', value: stats.total_executions.toLocaleString(), color: 'text-jarvis-text-bright' },
            { label: 'Avg Trust', value: `${(stats.avg_trust_score * 100).toFixed(0)}%`, color: 'text-yellow-400' },
          ].map((s) => (
            <GlassPanel key={s.label} className="p-3 text-center">
              <div className={`text-lg font-mono font-bold ${s.color}`}>{s.value}</div>
              <div className="text-[9px] font-mono text-jarvis-text-dim mt-0.5 uppercase tracking-widest">{s.label}</div>
            </GlassPanel>
          ))}
        </div>
      )}

      {/* Trending strip */}
      {trending.length > 0 && tab === 'all' && !search && (
        <div className="shrink-0 px-6 pb-3">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={11} className="text-jarvis-cyan" />
            <span className="text-[9px] font-mono text-jarvis-text-dim uppercase tracking-widest">Top by usage</span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
            {trending.map((s) => (
              <button
                key={s.skill_id}
                onClick={() => setSelectedSkill(s)}
                className="shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-jarvis-bg-3/60 border border-jarvis-border/30 hover:border-jarvis-cyan/30 transition-all duration-200 group"
              >
                <span className="text-sm">{s.icon ?? '⚡'}</span>
                <span className="text-[10px] font-mono text-jarvis-text group-hover:text-jarvis-cyan transition-colors">
                  {s.name}
                </span>
                <NeonBadge color="cyan" size="sm">{s.usage_count} uses</NeonBadge>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search + filter bar */}
      <div className="shrink-0 px-6 pb-3 flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-[180px]">
          <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-text-dim/40" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search skills…"
            className="w-full bg-jarvis-bg-3/60 border border-jarvis-border/40 rounded-lg pl-8 pr-3 py-2 text-xs font-mono text-jarvis-text placeholder-jarvis-text-dim/30 focus:outline-none focus:border-jarvis-cyan/40 transition-all duration-200"
          />
        </div>

        {/* Category filter */}
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-none">
          <Filter size={11} className="text-jarvis-text-dim/40 shrink-0" />
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`shrink-0 px-2.5 py-1 rounded-lg text-[10px] font-mono transition-all duration-200 ${
                category === cat
                  ? 'bg-jarvis-cyan/10 border border-jarvis-cyan/30 text-jarvis-cyan'
                  : 'text-jarvis-text-dim hover:text-jarvis-text border border-transparent hover:border-jarvis-border/30'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="shrink-0 px-6 pb-3 flex items-center gap-1 border-b border-jarvis-border/20">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-[10px] font-mono transition-all duration-200 border-b-2 ${
              tab === t.id
                ? 'text-jarvis-cyan border-jarvis-cyan bg-jarvis-cyan/5'
                : 'text-jarvis-text-dim border-transparent hover:text-jarvis-text'
            }`}
          >
            {t.label}
            {t.count !== undefined && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                tab === t.id ? 'bg-jarvis-cyan/20 text-jarvis-cyan' : 'bg-jarvis-bg-3/80 text-jarvis-text-dim'
              }`}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-6 py-4">
        {loading && skills.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 gap-3">
            <Loader2 size={20} className="text-jarvis-cyan animate-spin" />
            <span className="text-jarvis-text-dim text-xs font-mono">Loading skill registry…</span>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-40 gap-3">
            <AlertTriangle size={20} className="text-jarvis-red" />
            <span className="text-jarvis-red text-xs font-mono">{error}</span>
            <CockpitButton variant="ghost" size="sm" onClick={refresh}>Retry</CockpitButton>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <m.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-48 gap-4"
          >
            <div className="w-14 h-14 rounded-2xl bg-jarvis-bg-3/60 border border-jarvis-border/30 flex items-center justify-center">
              <Package size={24} className="text-jarvis-text-dim/40" />
            </div>
            <div className="text-center">
              <p className="text-jarvis-text-dim text-xs font-mono mb-1">
                {search || category !== 'All' ? 'No skills match your filters' : 'No skills registered yet'}
              </p>
              <p className="text-jarvis-text-dim/50 text-[10px] font-mono">
                {search ? 'Try a different search term' : 'Generate or import a skill to get started'}
              </p>
            </div>
            {!search && (
              <div className="flex items-center gap-2">
                <CockpitButton
                  variant="primary"
                  size="sm"
                  onClick={() => setShowGenInput(true)}
                  icon={<Zap size={11} />}
                >
                  Generate Skill
                </CockpitButton>
                <CockpitButton
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowGitHubModal(true)}
                  icon={<GitFork size={11} />}
                >
                  Import
                </CockpitButton>
              </div>
            )}
          </m.div>
        )}

        {filtered.length > 0 && (
          <m.div
            layout
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            <AnimatePresence mode="popLayout">
              {filtered.map((skill, i) => (
                <m.div
                  key={skill.skill_id}
                  layout
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: i * 0.04, duration: 0.25 }}
                >
                  <SkillCard
                    skill={skill}
                    onViewDetail={() => setSelectedSkill(skill)}
                    onInstall={() => toggleSkill(skill.skill_id, true).then(refresh)}
                    onUninstall={() => toggleSkill(skill.skill_id, false).then(refresh)}
                  />
                </m.div>
              ))}
            </AnimatePresence>
          </m.div>
        )}
      </div>

      {/* Modals */}
      <AnimatePresence>
        {showGitHubModal && (
          <GitHubImportModal
            key="gh-modal"
            onClose={() => setShowGitHubModal(false)}
            onImported={refresh}
          />
        )}
        {selectedSkill && (
          <SkillDetailModal
            key={`detail-${selectedSkill.skill_id}`}
            skill={selectedSkill}
            onClose={() => setSelectedSkill(null)}
            onRefresh={() => {
              refresh();
              // Re-select fresh data after refresh
              setSelectedSkill((prev) =>
                prev ? (skills.find((s) => s.skill_id === prev.skill_id) ?? prev) : null,
              );
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
