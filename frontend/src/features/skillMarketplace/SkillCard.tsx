import { useState } from 'react';
import { m } from 'framer-motion';
import {
  Star, Download, Trash2, Globe, Code2, Zap, CheckCircle, XCircle,
  Clock, BarChart3, Tag, GitBranch, Eye,
} from 'lucide-react';
import type { Skill } from './types';

interface SkillCardProps {
  skill: Skill;
  onInstall?: (skill: Skill) => void;
  onUninstall?: (skill: Skill) => void;
  onRate?: (skill: Skill, rating: number) => void;
  onPublish?: (skill: Skill) => void;
  onEvolve?: (skill: Skill) => void;
  onViewDetail?: (skill: Skill) => void;
  isInstalling?: boolean;
}

function TrustBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.7 ? 'bg-emerald-400' :
    score >= 0.4 ? 'bg-amber-400' :
    'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-white/60">{pct}%</span>
    </div>
  );
}

function StarRating({ rating, count, onRate }: { rating: number; count: number; onRate?: (r: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map(n => (
        <button
          key={n}
          className={`transition-colors ${(hover || rating) >= n ? 'text-amber-400' : 'text-white/20'}`}
          onMouseEnter={() => onRate && setHover(n)}
          onMouseLeave={() => onRate && setHover(0)}
          onClick={() => onRate?.(n)}
        >
          <Star className="w-3.5 h-3.5" fill={(hover || rating) >= n ? 'currentColor' : 'none'} />
        </button>
      ))}
      {count > 0 && <span className="text-xs text-white/40 ml-1">({count})</span>}
    </div>
  );
}

const ORIGIN_COLORS: Record<string, string> = {
  generated: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  github_import: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  user: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  evolved: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  self_growing: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
  builtin: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
};

export function SkillCard({
  skill,
  onInstall,
  onUninstall,
  onRate,
  onPublish,
  onEvolve,
  onViewDetail,
  isInstalling = false,
}: SkillCardProps) {
  const originClass = ORIGIN_COLORS[skill.origin] || ORIGIN_COLORS.generated;
  const successRate = skill.execution_count > 0
    ? Math.round((skill.success_count / skill.execution_count) * 100)
    : null;

  return (
    <m.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative bg-white/5 border border-white/10 rounded-xl p-4 hover:border-violet-500/40 hover:bg-white/8 transition-all group"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="text-sm font-semibold text-white truncate">{skill.name}</h3>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-medium ${originClass}`}>
              {skill.origin}
            </span>
            {skill.published && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-emerald-500/20 text-emerald-300 border-emerald-500/30 font-medium flex items-center gap-0.5">
                <Globe className="w-2.5 h-2.5" /> public
              </span>
            )}
            {!skill.enabled && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-red-500/20 text-red-300 border-red-500/30">
                disabled
              </span>
            )}
          </div>
          <p className="text-xs text-white/50 line-clamp-2 leading-relaxed">{skill.description}</p>
        </div>
        <div className="flex items-center gap-1 ml-2 flex-shrink-0">
          {skill.version > 1 && (
            <span className="text-[10px] text-white/30 flex items-center gap-0.5">
              <GitBranch className="w-2.5 h-2.5" /> v{skill.version}
            </span>
          )}
        </div>
      </div>

      {/* Trust score */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-white/40 uppercase tracking-wider">Trust Score</span>
          <span className="text-[10px] text-white/40">{skill.category}</span>
        </div>
        <TrustBar score={skill.trust_score} />
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-3 mb-3 text-xs text-white/40">
        {successRate !== null && (
          <span className="flex items-center gap-1">
            {successRate >= 70
              ? <CheckCircle className="w-3 h-3 text-emerald-400" />
              : <XCircle className="w-3 h-3 text-red-400" />}
            {successRate}% success
          </span>
        )}
        {skill.execution_count > 0 && (
          <span className="flex items-center gap-1">
            <BarChart3 className="w-3 h-3" />
            {skill.execution_count} runs
          </span>
        )}
        {skill.latency_ms_avg > 0 && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {Math.round(skill.latency_ms_avg)}ms
          </span>
        )}
        {skill.repo_url && (
          <a
            href={skill.repo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 hover:text-blue-400 transition-colors"
          >
            <Code2 className="w-3 h-3" /> src
          </a>
        )}
      </div>

      {/* Tags */}
      {skill.tags.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap mb-3">
          <Tag className="w-3 h-3 text-white/20" />
          {skill.tags.slice(0, 5).map(tag => (
            <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 text-white/40 border border-white/10">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Rating */}
      <div className="flex items-center justify-between mb-3">
        <StarRating rating={skill.user_rating} count={skill.rating_count} onRate={r => onRate?.(skill, r)} />
        <span className="text-[10px] text-white/30">
          {skill.user_rating > 0 ? skill.user_rating.toFixed(1) : 'No ratings'}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => onViewDetail?.(skill)}
          className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-white/60 hover:text-white transition-all"
        >
          <Eye className="w-3.5 h-3.5" /> Detail
        </button>
        {skill.enabled ? (
          <button
            onClick={() => onUninstall?.(skill)}
            className="flex items-center gap-1 px-2 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-xs text-red-300 transition-all"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        ) : (
          <button
            onClick={() => onInstall?.(skill)}
            disabled={isInstalling}
            className="flex items-center gap-1 px-2 py-1.5 rounded-lg bg-violet-500/20 hover:bg-violet-500/30 text-xs text-violet-300 transition-all disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        )}
        {!skill.published && skill.enabled && (
          <button
            onClick={() => onPublish?.(skill)}
            className="flex items-center gap-1 px-2 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-xs text-emerald-300 transition-all"
          >
            <Globe className="w-3.5 h-3.5" />
          </button>
        )}
        {skill.trust_score < 0.35 && skill.execution_count >= 3 && (
          <button
            onClick={() => onEvolve?.(skill)}
            className="flex items-center gap-1 px-2 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-xs text-amber-300 transition-all"
            title="Auto-evolve (rewrite) this skill"
          >
            <Zap className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </m.div>
  );
}
