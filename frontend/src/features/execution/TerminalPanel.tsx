import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

type Language = 'python' | 'shell';

interface ExecResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  durationMs: number;
  timedOut: boolean;
  language: string;
}

interface ExecStatus {
  enabled: boolean;
  languages: string[];
  timeoutSeconds: number;
  networkDisabled: boolean;
  outputLimitBytes: number;
}

interface HistoryEntry {
  code: string;
  language: Language;
  result: ExecResult;
  timestamp: string;
}

const STARTER: Record<Language, string> = {
  python: '# Python sandbox\nimport sys\nprint(f"Python {sys.version}")\nprint("Hello from JARVIS!")\n',
  shell: '# Shell sandbox\necho "Hello from JARVIS!"\nuname -a\n',
};

export function TerminalPanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const [language, setLanguage] = useState<Language>('python');
  const [code, setCode] = useState(STARTER.python);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const outputRef = useRef<HTMLDivElement>(null);

  const { data: status } = useQuery<ExecStatus>({
    queryKey: ['execution-status'],
    queryFn: () => apiClient.get<ExecStatus>('/execution/status'),
    enabled: bootstrapReady,
    staleTime: 60_000,
  });

  const runMut = useMutation({
    mutationFn: (vars: { code: string; language: Language }) =>
      apiClient.post<ExecResult>('/execution/run', vars),
    onSuccess: (result, vars) => {
      setHistory((h) => [
        { code: vars.code, language: vars.language, result, timestamp: new Date().toISOString() },
        ...h.slice(0, 49),
      ]);
      setTimeout(() => outputRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    },
  });

  const handleLangChange = (lang: Language) => {
    setLanguage(lang);
    setCode(STARTER[lang]);
  };

  const run = useCallback(() => {
    if (code.trim()) runMut.mutate({ code, language });
  }, [code, language, runMut]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      run();
    }
  };

  const latest = runMut.data;

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-0 shrink-0">
        <SectionHeader
          title="Execution Sandbox"
          subtitle={status ? `${status.languages.join(', ')} · ${status.timeoutSeconds}s timeout` : 'Loading…'}
        />
      </div>

      <div className="flex-1 flex flex-col min-h-0 p-4 gap-3">
        {/* Controls */}
        <div className="flex items-center gap-2 shrink-0">
          {(['python', 'shell'] as Language[]).map((lang) => (
            <button
              key={lang}
              onClick={() => handleLangChange(lang)}
              className={[
                'px-3 py-1 text-xs font-mono rounded border transition-colors',
                language === lang
                  ? 'border-jarvis-cyan text-jarvis-cyan bg-jarvis-cyan/10'
                  : 'border-jarvis-border text-jarvis-text-dim hover:border-jarvis-cyan/40',
              ].join(' ')}
            >
              {lang}
            </button>
          ))}
          <div className="flex-1" />
          <button
            onClick={run}
            disabled={!code.trim() || runMut.isPending || status?.enabled === false}
            className="btn-cockpit-primary px-4 py-1.5 text-sm"
          >
            {runMut.isPending ? '▶ Running…' : '▶ Run  (Ctrl+↵)'}
          </button>
        </div>

        {/* Editor */}
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={handleKeyDown}
          spellCheck={false}
          rows={12}
          className="flex-none font-mono text-xs bg-jarvis-bg border border-jarvis-border rounded p-3 text-jarvis-text-bright resize-none focus:outline-none focus:border-jarvis-cyan/60 overflow-auto"
          style={{ tabSize: 4 }}
        />

        {/* Output */}
        {(latest || runMut.isPending) && (
          <div ref={outputRef} className="jarvis-panel flex-1 min-h-0 overflow-auto p-3">
            {runMut.isPending ? (
              <p className="text-jarvis-text-dim text-xs font-mono animate-pulse">Running…</p>
            ) : latest ? (
              <OutputBlock result={latest} />
            ) : null}
          </div>
        )}

        {status?.enabled === false && (
          <p className="text-jarvis-red text-xs font-mono">
            Execution sandbox is disabled (SANDBOX_ENABLED=false).
          </p>
        )}
      </div>
    </div>
  );
}

function OutputBlock({ result }: { result: ExecResult }) {
  const exitOk = result.exitCode === 0 && !result.timedOut;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 text-xs font-mono">
        <span className={exitOk ? 'text-jarvis-cyan' : 'text-jarvis-red'}>
          exit {result.exitCode}
        </span>
        <span className="text-jarvis-text-dim">{result.durationMs}ms</span>
        {result.timedOut && <span className="text-jarvis-red">timed out</span>}
      </div>
      {result.stdout && (
        <pre className="text-jarvis-text-bright text-xs font-mono whitespace-pre-wrap break-words">
          {result.stdout}
        </pre>
      )}
      {result.stderr && (
        <pre className="text-jarvis-red text-xs font-mono whitespace-pre-wrap break-words">
          {result.stderr}
        </pre>
      )}
    </div>
  );
}
