/**
 * DiffBlock — renders a single file edit as a diff-style code block.
 * Shows added/removed lines with syntax highlighting colors.
 */
import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, FileCode2, Copy, Check } from 'lucide-react';
import type { CodeEdit } from './agentRunTypes';

interface Props {
  edit: CodeEdit;
  index: number;
}

export function DiffBlock({ edit, index }: Props) {
  const [expanded, setExpanded] = useState(index < 3);
  const [copied, setCopied] = useState(false);

  const lines = edit.diff
    ? parseDiff(edit.diff)
    : edit.content.split('\n').map((l) => ({ type: 'add' as const, text: l }));

  const added   = lines.filter((l) => l.type === 'add').length;
  const removed = lines.filter((l) => l.type === 'remove').length;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(edit.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <m.div
      className="border border-jarvis-border/40 rounded-xl overflow-hidden bg-jarvis-bg-2/60"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
    >
      {/* Header */}
      <button
        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-jarvis-bg-3/40 transition-colors duration-150"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="text-jarvis-text-dim shrink-0">
          {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </span>
        <FileCode2 size={13} className="text-jarvis-cyan shrink-0" />
        <span className="text-jarvis-cyan text-xs font-mono truncate flex-1 text-left">
          {edit.path}
        </span>

        {/* +/- stats */}
        <span className="flex items-center gap-2 shrink-0">
          {added > 0 && (
            <span className="text-[10px] font-mono text-green-400">+{added}</span>
          )}
          {removed > 0 && (
            <span className="text-[10px] font-mono text-jarvis-red">-{removed}</span>
          )}
          <span className="text-[10px] font-mono text-jarvis-text-dim px-1.5 py-0.5 rounded border border-jarvis-border/30 bg-jarvis-bg/60">
            {edit.mode}
          </span>
        </span>

        {/* Copy button */}
        <button
          onClick={(e) => { e.stopPropagation(); handleCopy(); }}
          className="text-jarvis-text-dim hover:text-jarvis-cyan transition-colors p-1 rounded"
          title="Copy content"
        >
          {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
        </button>
      </button>

      {/* Code body */}
      <AnimatePresence initial={false}>
        {expanded && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="overflow-x-auto border-t border-jarvis-border/30">
              <table className="w-full text-[11px] font-mono">
                <tbody>
                  {lines.map((line, i) => (
                    <tr
                      key={i}
                      className={
                        line.type === 'add'
                          ? 'bg-green-950/30'
                          : line.type === 'remove'
                          ? 'bg-red-950/30'
                          : ''
                      }
                    >
                      {/* Line number */}
                      <td className="select-none text-jarvis-text-dim/40 text-right pr-3 pl-3 py-0.5 w-8 shrink-0 border-r border-jarvis-border/20">
                        {i + 1}
                      </td>
                      {/* Diff marker */}
                      <td className="px-2 py-0.5 w-4 shrink-0">
                        {line.type === 'add' ? (
                          <span className="text-green-400">+</span>
                        ) : line.type === 'remove' ? (
                          <span className="text-jarvis-red">-</span>
                        ) : (
                          <span className="text-transparent"> </span>
                        )}
                      </td>
                      {/* Content */}
                      <td
                        className={[
                          'py-0.5 pr-4 whitespace-pre',
                          line.type === 'add'
                            ? 'text-green-300'
                            : line.type === 'remove'
                            ? 'text-red-300 line-through opacity-60'
                            : 'text-jarvis-text-bright',
                        ].join(' ')}
                      >
                        {line.text}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </m.div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

type DiffLine = { type: 'add' | 'remove' | 'context'; text: string };

function parseDiff(diff: string): DiffLine[] {
  return diff.split('\n').flatMap((line): DiffLine[] => {
    if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) return [];
    if (line.startsWith('+')) return [{ type: 'add', text: line.slice(1) }];
    if (line.startsWith('-')) return [{ type: 'remove', text: line.slice(1) }];
    return [{ type: 'context', text: line.startsWith(' ') ? line.slice(1) : line }];
  });
}
