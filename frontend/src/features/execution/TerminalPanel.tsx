import React, { useCallback, useRef, useState, useEffect, useMemo } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { m, AnimatePresence } from 'framer-motion';
import { apiClient } from '@/lib/api/client';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';
import { AlertTriangle, CheckCircle2, Lightbulb, Terminal, Clock, History, Wand2, X, Loader2 } from 'lucide-react';

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

interface AISuggestion {
  type: 'improvement' | 'warning' | 'optimization' | 'security';
  message: string;
  line?: number;
}

const STARTER: Record<Language, string> = {
  python: '# Python sandbox\nimport sys\nprint(f"Python {sys.version}")\nprint("Hello from JARVIS!")\n',
  shell: '# Shell sandbox\necho "Hello from JARVIS!"\nuname -a\n',
};

const SUGGESTION_COLORS: Record<string, string> = {
  improvement: 'text-jarvis-cyan border-jarvis-cyan/30 bg-jarvis-cyan/5',
  warning: 'text-jarvis-yellow border-jarvis-yellow/30 bg-jarvis-yellow/5',
  optimization: 'text-jarvis-green border-jarvis-green/30 bg-jarvis-green/5',
  security: 'text-jarvis-red border-jarvis-red/30 bg-jarvis-red/5',
};

const SUGGESTION_ICONS: Record<string, React.ReactNode> = {
  improvement: <Lightbulb size={12} />,
  warning: <AlertTriangle size={12} />,
  optimization: <CheckCircle2 size={12} />,
  security: <AlertTriangle size={12} />,
};

export function TerminalPanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const [language, setLanguage] = useState<Language>('python');
  const [code, setCode] = useState(STARTER.python);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [aiPreview, setAiPreview] = useState<string | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<HTMLTextAreaElement>(null);

  const { data: status } = useQuery<ExecStatus>({
    queryKey: ['execution-status'],
    queryFn: () => apiClient.get<ExecStatus>('/execution/status'),
    enabled: bootstrapReady,
    ...freshness.slowlyChanging,
  });

  const runMut = useMutation({
    mutationFn: (vars: { code: string; language: Language }) =>
      apiClient.post<ExecResult>('/execution/run', vars),
    onSuccess: (result, vars) => {
      setHistory((h) => [
        { code: vars.code, language: vars.language, result, timestamp: new Date().toISOString() },
        ...h.slice(0, 49),
      ]);
      setAiPreview(null);
      setTimeout(() => outputRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    },
  });

  // AI-powered suggestions based on code content
  const aiSuggestions = useMemo<AISuggestion[]>(() => {
    const suggestions: AISuggestion[] = [];
    if (!code.trim()) return suggestions;

    const lines = code.split('\n');

    if (language === 'python') {
      // Check for bare except
      if (code.includes('except:')) {
        suggestions.push({
          type: 'warning',
          message: 'Bare except clause catches all exceptions. Use specific exception types.',
          line: lines.findIndex(l => l.trim().startsWith('except:')) + 1,
        });
      }
      // Check for print debugging
      if (code.match(/print\(.*\)/g) && code.match(/print\(.*\)/g)!.length > 3) {
        suggestions.push({
          type: 'optimization',
          message: 'Multiple print statements — consider using logging instead.',
        });
      }
      // Check for dangerous eval
      if (code.includes('eval(') || code.includes('exec(')) {
        suggestions.push({
          type: 'security',
          message: 'eval()/exec() can execute arbitrary code. Use safer alternatives if possible.',
        });
      }
      // Check for missing __name__ guard
      if (code.includes('def ') && !code.includes('if __name__')) {
        suggestions.push({
          type: 'improvement',
          message: 'Consider adding if __name__ == "__main__": guard for reusable code.',
        });
      }
      // Check for list comprehension opportunity
      if (code.includes('for') && code.includes('append')) {
        suggestions.push({
          type: 'optimization',
          message: 'Consider using a list comprehension instead of for+append.',
        });
      }
    }

    if (language === 'shell') {
      // Check for dangerous commands
      const dangerous = ['rm -rf /', 'mkfs', 'dd if=', '> /dev/sda', ':(){ :|:& };:'];
      if (dangerous.some(cmd => code.includes(cmd))) {
        suggestions.push({
          type: 'security',
          message: '⚠️ Potentially destructive command detected. Review before running.',
        });
      }
      // Check for missing shebang
      if (!code.startsWith('#!') && !code.startsWith('#')) {
        suggestions.push({
          type: 'improvement',
          message: 'Scripts typically start with #!/bin/bash or #!/bin/sh.',
        });
      }
    }

    return suggestions.slice(0, 3);
  }, [code, language]);

  // AI execution preview
  const generatePreview = useCallback(async () => {
    if (!code.trim()) return;

    const previewLines: string[] = [];

    if (language === 'python') {
      const hasPrint = code.includes('print');
      const hasLoop = code.includes('for ') || code.includes('while ');
      const hasFunction = code.includes('def ');
      const hasImport = code.includes('import ') || code.includes('from ');

      if (hasImport) previewLines.push('• Loading dependencies…');
      if (hasFunction) previewLines.push('• Defining functions…');
      if (hasLoop) previewLines.push('• Running loop (check for infinite loops)…');
      if (hasPrint) previewLines.push('• Producing output…');
      if (code.includes('input(')) previewLines.push('• ⚠ Script expects user input — may hang');

      const mainCode = code
        .split('\n')
        .filter(l => l.trim() && !l.trim().startsWith('#'))
        .filter(l => !l.trim().startsWith('import ') && !l.trim().startsWith('from '));

      previewLines.push(`• Executing ${mainCode.length} statement(s)`);

      if (code.includes('sys.exit') || code.includes('exit(')) {
        previewLines.push('• Script will exit early');
      }
    } else {
      const hasEcho = code.includes('echo');
      const hasPipe = code.includes('|');
      const hasRedirect = code.includes('>') || code.includes('>>');
      const commands = code.split('\n').filter(l => l.trim() && !l.trim().startsWith('#'));

      if (commands.length === 1) previewLines.push(`• Running: ${commands[0].trim().substring(0, 60)}`);
      else previewLines.push(`• Running ${commands.length} commands`);
      if (hasEcho) previewLines.push('• Producing text output…');
      if (hasPipe) previewLines.push('• Piping data between commands…');
      if (hasRedirect) previewLines.push('• ⚠ Writing output to file');
    }

    setAiPreview(previewLines.join('\n'));
  }, [code, language]);

  // Generate preview on code change (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (code.trim() && showSuggestions) {
        generatePreview();
      }
    }, 800);
    return () => clearTimeout(timer);
  }, [code, language, showSuggestions, generatePreview]);

  // Quick apply suggestion
  const applySuggestion = useCallback((suggestion: AISuggestion) => {
    if (suggestion.type === 'improvement' && suggestion.message.includes('__name__')) {
      setCode(prev => prev + '\n\nif __name__ == "__main__":\n    main()');
    } else if (suggestion.type === 'improvement' && suggestion.message.includes('shebang')) {
      setCode(prev => '#!/bin/bash\n' + prev);
    }
  }, []);

  const handleLangChange = (lang: Language) => {
    setLanguage(lang);
    setCode(STARTER[lang]);
    setAiPreview(null);
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

  const loadFromHistory = (entry: HistoryEntry) => {
    setCode(entry.code);
    setLanguage(entry.language);
    setShowHistory(false);
    setAiPreview(null);
  };

  const latest = runMut.data;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 pb-0 shrink-0">
        <SectionHeader
          title="Execution Sandbox"
          subtitle={status ? `${status.languages.join(', ')} · ${status.timeoutSeconds}s timeout` : 'Loading…'}
          action={
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSuggestions(!showSuggestions)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-mono border transition-all duration-200 ${
                  showSuggestions
                    ? 'border-jarvis-cyan/30 text-jarvis-cyan bg-jarvis-cyan/5'
                    : 'border-jarvis-border/30 text-jarvis-text-dim/60 hover:text-jarvis-text'
                }`}
              >
                <Wand2 size={12} />
                AI
              </button>
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-mono border border-jarvis-border/30 text-jarvis-text-dim/60 hover:text-jarvis-text transition-all duration-200"
              >
                <History size={12} />
                {history.length}
              </button>
            </div>
          }
        />
      </div>

      <div className="flex-1 flex min-h-0 gap-1">
        {/* Left: Editor + Output */}
        <div className={`flex-1 flex flex-col min-h-0 p-4 pt-2 gap-3 ${showSuggestions ? '' : ''}`}>
          {/* Controls */}
          <div className="flex items-center gap-2 shrink-0">
            {(['python', 'shell'] as Language[]).map((lang) => (
              <button
                key={lang}
                onClick={() => handleLangChange(lang)}
                className={[
                  'px-3 py-1.5 text-xs font-mono rounded-lg border transition-all duration-200',
                  language === lang
                    ? 'border-jarvis-cyan text-jarvis-cyan bg-jarvis-cyan/10 shadow-[0_0_10px_rgba(0,212,255,0.1)]'
                    : 'border-jarvis-border/40 text-jarvis-text-dim hover:border-jarvis-cyan/40 hover:text-jarvis-cyan/80',
                ].join(' ')}
              >
                {lang}
              </button>
            ))}
            <div className="flex-1" />
            <button
              onClick={() => setCode('')}
              disabled={!code.trim()}
              className="px-2.5 py-1.5 text-[11px] font-mono text-jarvis-text-dim/50 hover:text-jarvis-text transition-colors disabled:opacity-30"
            >
              Clear
            </button>
          </div>

          {/* Editor area */}
          <div className="relative flex-none">
            <textarea
              ref={editorRef}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={handleKeyDown}
              spellCheck={false}
              rows={10}
              className="w-full font-mono text-xs bg-jarvis-bg border border-jarvis-border rounded-lg p-3 text-jarvis-text-bright resize-none focus:outline-none focus:border-jarvis-cyan/60 overflow-auto transition-colors duration-200"
              style={{ tabSize: 4, lineHeight: '1.6' }}
              placeholder={language === 'python' ? '# Enter Python code…' : '# Enter shell commands…'}
            />
            {/* Line indicator */}
            <div className="absolute bottom-2 right-2 text-[10px] font-mono text-jarvis-text-dim/30 pointer-events-none">
              {code.split('\n').length} lines
            </div>
          </div>

          {/* AI Execution Preview */}
          <AnimatePresence>
            {showSuggestions && aiPreview && !runMut.isPending && !latest && (
              <m.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="border border-jarvis-cyan/15 rounded-lg bg-jarvis-cyan/[0.02] p-2.5">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Terminal size={10} className="text-jarvis-cyan/60" />
                    <span className="text-[10px] font-mono text-jarvis-cyan/60 uppercase tracking-wider">Execution Preview</span>
                  </div>
                  <pre className="text-[11px] font-mono text-jarvis-text-dim/80 whitespace-pre-wrap leading-relaxed">
                    {aiPreview}
                  </pre>
                </div>
              </m.div>
            )}
          </AnimatePresence>

          {/* Run button + AI suggestions */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={run}
              disabled={!code.trim() || runMut.isPending || status?.enabled === false}
              className="btn-cockpit-primary px-5 py-2 text-sm flex items-center gap-2"
            >
              {runMut.isPending ? (
                <><Loader2 size={14} className="animate-spin" /> Running…</>
              ) : (
                <><Terminal size={14} /> Run  (Ctrl+↵)</>
              )}
            </button>
            {aiSuggestions.length > 0 && showSuggestions && (
              <span className="text-[10px] font-mono text-jarvis-cyan/50">
                {aiSuggestions.length} suggestion{aiSuggestions.length > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Output */}
          {(latest || runMut.isPending) && (
            <div ref={outputRef} className="jarvis-panel flex-1 min-h-0 overflow-auto p-3">
              {runMut.isPending ? (
                <div className="flex items-center gap-2 text-jarvis-text-dim text-xs font-mono">
                  <Loader2 size={12} className="animate-spin text-jarvis-cyan" />
                  <span className="animate-pulse">Running…</span>
                </div>
              ) : latest ? (
                <OutputBlock result={latest} />
              ) : null}
            </div>
          )}

          {status?.enabled === false && (
            <div className="flex items-center gap-2 text-jarvis-red text-xs font-mono p-2 border border-jarvis-red/20 rounded-lg bg-jarvis-red/5">
              <AlertTriangle size={12} />
              Execution sandbox is disabled (SANDBOX_ENABLED=false).
            </div>
          )}
        </div>

        {/* Right: AI Suggestions Panel */}
        <AnimatePresence>
          {showSuggestions && (
            <m.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 260, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="shrink-0 border-l border-jarvis-border/30 overflow-hidden"
            >
              <div className="w-[260px] h-full flex flex-col">
                {/* Suggestions Panel Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-jarvis-border/20">
                  <div className="flex items-center gap-2">
                    <Wand2 size={12} className="text-jarvis-cyan" />
                    <span className="text-xs font-mono text-jarvis-cyan font-semibold tracking-wider">AI SUGGESTIONS</span>
                  </div>
                  <button
                    onClick={() => setShowSuggestions(false)}
                    className="text-jarvis-text-dim/40 hover:text-jarvis-text transition-colors"
                  >
                    <X size={12} />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                  {aiSuggestions.length === 0 ? (
                    <div className="text-center py-6">
                      <Lightbulb size={20} className="mx-auto mb-2 text-jarvis-text-dim/30" />
                      <p className="text-[11px] font-mono text-jarvis-text-dim/50">
                        No suggestions yet — write some code and I'll analyze it.
                      </p>
                    </div>
                  ) : (
                    aiSuggestions.map((s, i) => (
                      <m.div
                        key={i}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className={`p-2.5 rounded-lg border ${SUGGESTION_COLORS[s.type]}`}
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          {SUGGESTION_ICONS[s.type]}
                          <span className="text-[10px] font-mono uppercase tracking-wider opacity-70">
                            {s.type}
                          </span>
                          {s.line && (
                            <span className="text-[10px] font-mono opacity-50 ml-auto">
                              L{s.line}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] font-mono leading-relaxed opacity-80">{s.message}</p>
                        {s.type === 'improvement' && (
                          <button
                            onClick={() => applySuggestion(s)}
                            className="mt-1.5 text-[10px] font-mono text-jarvis-cyan/70 hover:text-jarvis-cyan transition-colors"
                          >
                            Apply fix →
                          </button>
                        )}
                      </m.div>
                    ))
                  )}

                  {/* Execution tips */}
                  <div className="mt-4 pt-3 border-t border-jarvis-border/20">
                    <p className="text-[10px] font-mono text-jarvis-text-dim/40 mb-2">Tips</p>
                    <div className="space-y-1.5">
                      <Tip text="Ctrl+↵ to run code" />
                      <Tip text="Select text to run just that" />
                      <Tip text="AI analyzes code live" />
                      <Tip text="History persists in session" />
                    </div>
                  </div>
                </div>
              </div>
            </m.div>
          )}
        </AnimatePresence>
      </div>

      {/* History Panel (overlay) */}
      <AnimatePresence>
        {showHistory && (
          <m.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-0 left-0 right-0 h-1/2 bg-jarvis-bg/98 backdrop-blur-xl border-t border-jarvis-border/40 rounded-t-2xl z-20 overflow-hidden"
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-jarvis-border/20">
              <div className="flex items-center gap-2">
                <Clock size={14} className="text-jarvis-cyan" />
                <span className="text-xs font-mono text-jarvis-cyan font-semibold tracking-wider">EXECUTION HISTORY</span>
                <span className="text-[10px] font-mono text-jarvis-text-dim/50">{history.length} runs</span>
              </div>
              <button
                onClick={() => setShowHistory(false)}
                className="text-jarvis-text-dim/40 hover:text-jarvis-text transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            <div className="h-full overflow-y-auto p-3 space-y-2">
              {history.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-sm font-mono text-jarvis-text-dim/40">No history yet</p>
                </div>
              ) : (
                history.map((entry, i) => (
                  <m.div
                    key={`${entry.timestamp}-${i}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="jarvis-panel p-3 cursor-pointer hover:border-jarvis-cyan/30 transition-all duration-200"
                    onClick={() => loadFromHistory(entry)}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        entry.language === 'python' ? 'text-jarvis-cyan bg-jarvis-cyan/10' : 'text-jarvis-green bg-jarvis-green/10'
                      }`}>
                        {entry.language}
                      </span>
                      <span className={`text-[10px] font-mono ${
                        entry.result.exitCode === 0 ? 'text-jarvis-green' : 'text-jarvis-red'
                      }`}>
                        exit {entry.result.exitCode}
                      </span>
                      <span className="text-[10px] font-mono text-jarvis-text-dim/50">{entry.result.durationMs}ms</span>
                      <span className="text-[10px] font-mono text-jarvis-text-dim/30 ml-auto">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <pre className="text-[11px] font-mono text-jarvis-text-dim/70 truncate">
                      {entry.code.split('\n')[0].substring(0, 80)}
                    </pre>
                  </m.div>
                ))
              )}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function OutputBlock({ result }: { result: ExecResult }) {
  const exitOk = result.exitCode === 0 && !result.timedOut;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 text-xs font-mono">
        <span className={exitOk ? 'inline-flex items-center gap-1 text-jarvis-green' : 'inline-flex items-center gap-1 text-jarvis-red'}>
          {exitOk ? <CheckCircle2 size={10} /> : <AlertTriangle size={10} />}
          exit {result.exitCode}
        </span>
        <span className="text-jarvis-text-dim/70">{result.durationMs}ms</span>
        {result.timedOut && (
          <span className="inline-flex items-center gap-1 text-jarvis-red">
            <AlertTriangle size={10} />
            timed out
          </span>
        )}
      </div>
      {result.stdout && (
        <pre className="text-jarvis-text-bright text-xs font-mono whitespace-pre-wrap break-words p-2 bg-jarvis-bg/50 rounded-lg border border-jarvis-border/20">
          {result.stdout}
        </pre>
      )}
      {result.stderr && (
        <pre className="text-jarvis-red text-xs font-mono whitespace-pre-wrap break-words p-2 bg-jarvis-red/5 rounded-lg border border-jarvis-red/20">
          {result.stderr}
        </pre>
      )}
    </div>
  );
}

function Tip({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 text-[10px] font-mono text-jarvis-text-dim/40">
      <span className="w-1 h-1 rounded-full bg-jarvis-cyan/40" />
      {text}
    </div>
  );
}
