import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { X, GitFork, Download, AlertTriangle, CheckCircle, Loader2, GitBranch, Package } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { useSkillMarketplace } from './useSkillMarketplace';

interface Props {
  onClose: () => void;
  onImported: () => void;
}

type ImportStatus = 'idle' | 'importing' | 'success' | 'error';

export function GitHubImportModal({ onClose, onImported }: Props) {
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState<ImportStatus>('idle');
  const [message, setMessage] = useState('');
  const [importedSkill, setImportedSkill] = useState<{ name: string; skill_id: string } | null>(null);
  const { importFromGitHub } = useSkillMarketplace();

  const isValidGitHubUrl = (u: string) => {
    try {
      const parsed = new URL(u);
      return parsed.hostname === 'github.com' && parsed.pathname.split('/').length >= 3;
    } catch {
      return false;
    }
  };

  const handleImport = async () => {
    if (!url.trim() || !isValidGitHubUrl(url.trim())) {
      setStatus('error');
      setMessage('Enter a valid GitHub repository URL (e.g. https://github.com/user/repo)');
      return;
    }

    setStatus('importing');
    setMessage('Cloning repository and analyzing skill manifest...');
    setImportedSkill(null);

    try {
      const result = await importFromGitHub(url.trim());
      if (result.skill_id) {
        setStatus('success');
        setImportedSkill({ name: result.name ?? 'Imported Skill', skill_id: result.skill_id });
        setMessage(result.message ?? 'Skill imported and registered successfully.');
        onImported();
      } else {
        setStatus('error');
        setMessage(result.detail ?? result.message ?? 'Import failed — no skill_id returned.');
      }
    } catch (err: any) {
      setStatus('error');
      setMessage(err?.message ?? 'Network error — AI service may be unreachable.');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && status !== 'importing') handleImport();
    if (e.key === 'Escape') onClose();
  };

  return (
    <m.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <m.div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />

      {/* Modal */}
      <m.div
        className="relative z-10 w-full max-w-lg"
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 24, scale: 0.97 }}
        transition={{ type: 'spring', stiffness: 320, damping: 28 }}
      >
        <GlassPanel className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-jarvis-cyan/10 border border-jarvis-cyan/20 flex items-center justify-center">
                <GitFork size={18} className="text-jarvis-cyan" />
              </div>
              <div>
                <h2 className="text-jarvis-text-bright text-sm font-mono font-bold tracking-wide">
                  Import from GitHub
                </h2>
                <p className="text-jarvis-text-dim text-[10px] font-mono mt-0.5">
                  Clone a repo, auto-detect skill manifest
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-lg text-jarvis-text-dim/40 hover:text-jarvis-red hover:bg-jarvis-red/10 transition-all duration-200"
            >
              <X size={14} />
            </button>
          </div>

          {/* URL Input */}
          <div className="mb-4">
            <label className="block text-[10px] font-mono text-jarvis-text-dim uppercase tracking-widest mb-2">
              Repository URL
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-text-dim/40">
                <GitBranch size={14} />
              </div>
              <input
                type="url"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (status === 'error') { setStatus('idle'); setMessage(''); }
                }}
                onKeyDown={handleKeyDown}
                placeholder="https://github.com/username/skill-repo"
                disabled={status === 'importing'}
                className="w-full bg-jarvis-bg-3/60 border border-jarvis-border/50 rounded-lg pl-9 pr-4 py-2.5 text-xs font-mono text-jarvis-text placeholder-jarvis-text-dim/30 focus:outline-none focus:border-jarvis-cyan/50 focus:ring-1 focus:ring-jarvis-cyan/20 transition-all duration-200 disabled:opacity-50"
              />
            </div>
          </div>

          {/* Info box */}
          <div className="mb-5 p-3 rounded-lg bg-jarvis-bg-3/40 border border-jarvis-border/30">
            <p className="text-[10px] font-mono text-jarvis-text-dim leading-relaxed">
              JARVIS will clone the repo, look for{' '}
              <span className="text-jarvis-cyan">skill.yaml</span>,{' '}
              <span className="text-jarvis-cyan">skill.json</span>, or{' '}
              <span className="text-jarvis-cyan">README.md</span> — and use the LLM to
              extract skill metadata if no manifest is found.
            </p>
          </div>

          {/* Status feedback */}
          <AnimatePresence mode="wait">
            {status !== 'idle' && (
              <m.div
                key={status}
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2 }}
                className={`mb-4 p-3 rounded-lg border flex items-start gap-3 ${
                  status === 'importing'
                    ? 'bg-jarvis-cyan/5 border-jarvis-cyan/20'
                    : status === 'success'
                    ? 'bg-green-500/5 border-green-500/20'
                    : 'bg-jarvis-red/5 border-jarvis-red/20'
                }`}
              >
                {status === 'importing' && (
                  <Loader2 size={14} className="text-jarvis-cyan mt-0.5 shrink-0 animate-spin" />
                )}
                {status === 'success' && (
                  <CheckCircle size={14} className="text-green-400 mt-0.5 shrink-0" />
                )}
                {status === 'error' && (
                  <AlertTriangle size={14} className="text-jarvis-red mt-0.5 shrink-0" />
                )}
                <div>
                  <p className={`text-xs font-mono ${
                    status === 'importing' ? 'text-jarvis-cyan' :
                    status === 'success' ? 'text-green-400' : 'text-jarvis-red'
                  }`}>
                    {message}
                  </p>
                  {status === 'success' && importedSkill && (
                    <div className="mt-2 flex items-center gap-2">
                      <Package size={11} className="text-jarvis-text-dim" />
                      <span className="text-[10px] font-mono text-jarvis-text-dim">
                        Registered as:{' '}
                        <span className="text-jarvis-cyan">{importedSkill.name}</span>
                        <span className="text-jarvis-text-dim/40 ml-1">
                          ({importedSkill.skill_id.slice(0, 8)}…)
                        </span>
                      </span>
                    </div>
                  )}
                </div>
              </m.div>
            )}
          </AnimatePresence>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3">
            <CockpitButton
              variant="ghost"
              size="sm"
              onClick={onClose}
            >
              Cancel
            </CockpitButton>

            {status === 'success' ? (
              <CockpitButton
                variant="primary"
                size="sm"
                onClick={onClose}
                icon={<CheckCircle size={13} />}
              >
                Done
              </CockpitButton>
            ) : (
              <CockpitButton
                variant="primary"
                size="sm"
                onClick={handleImport}
                disabled={status === 'importing' || !url.trim()}
                icon={status === 'importing'
                  ? <Loader2 size={13} className="animate-spin" />
                  : <Download size={13} />
                }
              >
                {status === 'importing' ? 'Importing…' : 'Import Skill'}
              </CockpitButton>
            )}
          </div>
        </GlassPanel>
      </m.div>
    </m.div>
  );
}
