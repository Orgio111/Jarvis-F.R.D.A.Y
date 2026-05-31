import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Zap, Brain, Sigma, Code2, Sparkles } from 'lucide-react';
import { m, AnimatePresence } from 'framer-motion';
import { useChatStore } from './chatStore';
import {
  ALL_MODES,
  MODE_LABELS,
  MODE_DESCRIPTIONS,
  MODE_COLORS,
  MODE_BG_COLORS,
  MODE_HOVER_COLORS,
} from './chatTypes';
import type { ChatMode } from './chatTypes';

const MODE_ICONS: Record<ChatMode, typeof Zap> = {
  fast: Zap,
  smart: Brain,
  deep: Sigma,
  coding: Code2,
};

interface Props {
  disabled?: boolean;
}

export function ModelSelector({ disabled = false }: Props) {
  const {
    selectedMode,
    setSelectedMode,
    manualModelId,
    setManualModelId,
    availableModes,
    isModesLoading,
  } = useChatStore();

  const [open, setOpen] = useState(false);
  const [modelDropdown, setModelDropdown] = useState<ChatMode | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setModelDropdown(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const currentModeInfo = availableModes.find((m) => m.mode === selectedMode);
  const resolvedModel = currentModeInfo?.resolved;
  const hasManualOverride = !!manualModelId;
  const Icon = MODE_ICONS[selectedMode];

  const handleSelectMode = (mode: ChatMode) => {
    setSelectedMode(mode);
    // If there was a manual override for this mode, clear it when switching
    if (manualModelId) setManualModelId('');
    setOpen(false);
    setModelDropdown(null);
  };

  const handleManualModel = (mode: ChatMode, modelId: string) => {
    setSelectedMode(mode);
    setManualModelId(modelId);
    setModelDropdown(null);
  };

  return (
    <div ref={ref} className="relative">
      {/* Mode trigger button */}
      <button
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className={[
          'flex items-center gap-2 px-3 py-1.5 rounded-lg text-[10px] font-mono font-semibold',
          'border transition-all duration-200 cursor-pointer',
          'tracking-wider uppercase',
          MODE_BG_COLORS[selectedMode],
          MODE_HOVER_COLORS[selectedMode],
          disabled ? 'opacity-50 cursor-not-allowed' : '',
        ].join(' ')}
        title={`Current mode: ${MODE_LABELS[selectedMode]}`}
      >
        <Icon size={12} className={MODE_COLORS[selectedMode]} />
        <span className={MODE_COLORS[selectedMode]}>{MODE_LABELS[selectedMode]}</span>
        {hasManualOverride && (
          <Sparkles size={10} className="text-jarvis-yellow/70" />
        )}
        <ChevronDown
          size={10}
          className={[
            'text-jarvis-text-dim/50 transition-transform duration-200',
            open ? 'rotate-180' : '',
          ].join(' ')}
        />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <m.div
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className={[
              'absolute top-full mt-1.5 right-0 z-50 min-w-[280px]',
              'rounded-xl border border-jarvis-border/50',
              'bg-jarvis-bg-2/95 backdrop-blur-xl shadow-2xl',
              'overflow-hidden',
            ].join(' ')}
          >
            <div className="px-3 py-2 border-b border-jarvis-border/30">
              <span className="text-[10px] font-mono text-jarvis-text-dim/60 tracking-wider uppercase">
                Model Mode
              </span>
            </div>

            {/* Mode list */}
            <div className="p-1.5 space-y-0.5">
              {ALL_MODES.map((mode) => {
                const modeInfo = availableModes.find((m) => m.mode === mode);
                const isActive = mode === selectedMode && !manualModelId;
                const ModeIcon = MODE_ICONS[mode];
                const hasModels = modeInfo?.availableModels && modeInfo.availableModels.length > 0;

                return (
                  <div key={mode} className="relative">
                    <div
                      onClick={() => handleSelectMode(mode)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleSelectMode(mode); }}
                      className={[
                        'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left',
                        'transition-all duration-150 cursor-pointer group',
                        isActive
                          ? MODE_BG_COLORS[mode]
                          : 'hover:bg-jarvis-bg-3/50',
                      ].join(' ')}
                    >
                      <ModeIcon
                        size={14}
                        className={[
                          'shrink-0',
                          isActive ? MODE_COLORS[mode] : 'text-jarvis-text-dim/50',
                        ].join(' ')}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className={[
                              'text-xs font-mono font-semibold tracking-wider',
                              isActive ? MODE_COLORS[mode] : 'text-jarvis-text-bright',
                            ].join(' ')}
                          >
                            {MODE_LABELS[mode]}
                          </span>
                          {modeInfo?.resolved && !isActive && (
                            <span className="text-[9px] font-mono text-jarvis-text-dim/40 truncate">
                              {modeInfo.resolved.modelName}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] font-mono text-jarvis-text-dim/60 mt-0.5 leading-tight">
                          {MODE_DESCRIPTIONS[mode]}
                        </p>
                      </div>

                      {/* Manual model button */}
                      {hasModels && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setModelDropdown(modelDropdown === mode ? null : mode);
                          }}
                          className={[
                            'shrink-0 px-2 py-1 rounded text-[9px] font-mono',
                            'border border-jarvis-border/30 text-jarvis-text-dim/50',
                            'hover:text-jarvis-cyan hover:border-jarvis-cyan/30',
                            'transition-all duration-150 cursor-pointer',
                            modelDropdown === mode ? 'border-jarvis-cyan/40 text-jarvis-cyan' : '',
                          ].join(' ')}
                          title="Override model"
                        >
                          Model ▾
                        </button>
                      )}
                    </div>

                    {/* Manual model sub-dropdown */}
                    <AnimatePresence>
                      {modelDropdown === mode && (
                        <m.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="pl-10 pr-3 pb-2 space-y-0.5">
                            {/* Auto option */}
                            <button
                              onClick={() => handleManualModel(mode, '')}
                              className={[
                                'w-full text-left px-2.5 py-1.5 rounded text-[10px] font-mono',
                                'transition-all duration-150 cursor-pointer',
                                manualModelId === '' || mode !== selectedMode
                                  ? 'text-jarvis-cyan/70 bg-jarvis-cyan/5'
                                  : 'text-jarvis-text-dim/50 hover:text-jarvis-text-bright hover:bg-jarvis-bg-3/50',
                              ].join(' ')}
                            >
                              ✦ Auto (mode default)
                            </button>
                            {modeInfo?.availableModels.map((mdl) => (
                              <button
                                key={mdl.id}
                                onClick={() => handleManualModel(mode, mdl.id)}
                                className={[
                                  'w-full text-left px-2.5 py-1.5 rounded text-[10px] font-mono',
                                  'transition-all duration-150 cursor-pointer flex items-center gap-2',
                                  mdl.id === manualModelId && mode === selectedMode
                                    ? 'text-jarvis-cyan bg-jarvis-cyan/10'
                                    : 'text-jarvis-text-dim/60 hover:text-jarvis-text-bright hover:bg-jarvis-bg-3/50',
                                ].join(' ')}
                              >
                                <span className="truncate flex-1">{mdl.name}</span>
                                <span className="text-[8px] text-jarvis-text-dim/30 shrink-0 uppercase">
                                  {mdl.providerId}
                                </span>
                                {mdl.isFree && (
                                  <span className="text-[8px] text-jarvis-cyan border border-jarvis-cyan/20 rounded px-1 shrink-0">
                                    free
                                  </span>
                                )}
                              </button>
                            ))}
                          </div>
                        </m.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>

            {/* Loading state */}
            {isModesLoading && (
              <div className="px-3 py-2 border-t border-jarvis-border/30">
                <span className="text-[10px] font-mono text-jarvis-text-dim/40 italic">
                  Discovering available models…
                </span>
              </div>
            )}

            {/* Current model info */}
            {resolvedModel && !isModesLoading && (
              <div className="px-3 py-2 border-t border-jarvis-border/30 flex items-center gap-2">
                <div className="w-1 h-1 rounded-full bg-jarvis-cyan/50" />
                <span className="text-[9px] font-mono text-jarvis-text-dim/50 truncate flex-1">
                  {hasManualOverride ? 'Override: ' : ''}
                  {resolvedModel.modelName}
                </span>
                <span className="text-[8px] font-mono text-jarvis-text-dim/30 shrink-0">
                  {resolvedModel.providerName}
                </span>
              </div>
            )}
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}
