import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useBootstrap } from './useBootstrap';
import { useBootstrapStore } from './bootstrapStore';
import { RecoveryScreen } from './RecoveryScreen';

interface Props {
  children: React.ReactNode;
}

/**
 * BootstrapGate renders its children only after a successful bootstrap.
 * Shows a loading animation while bootstrapping.
 * Shows RecoveryScreen on persistent failure.
 */
export function BootstrapGate({ children }: Props) {
  const { status } = useBootstrap();
  const { error, retryCount } = useBootstrapStore();

  return (
    <AnimatePresence mode="wait">
      {status === 'ready' ? (
        <motion.div
          key="app"
          className="w-full h-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        >
          {children}
        </motion.div>
      ) : status === 'error' && retryCount >= 3 ? (
        <motion.div
          key="recovery"
          className="w-full h-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <RecoveryScreen error={error ?? 'Unknown error'} retryCount={retryCount} />
        </motion.div>
      ) : (
        <motion.div
          key="loading"
          className="w-full h-full flex items-center justify-center bg-jarvis-bg"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <BootstrapLoader status={status} retryCount={retryCount} />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function BootstrapLoader({
  status,
  retryCount,
}: {
  status: string;
  retryCount: number;
}) {
  return (
    <div className="flex flex-col items-center gap-8">
      {/* JARVIS logo / spinner */}
      <div className="relative w-24 h-24">
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-jarvis-cyan opacity-30"
          animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0.1, 0.3] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute inset-2 rounded-full border-2 border-jarvis-cyan opacity-60"
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div
          className="absolute inset-4 rounded-full border-t-2 border-jarvis-blue"
          animate={{ rotate: -360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-jarvis-cyan text-xs font-mono font-bold neon-cyan">J</span>
        </div>
      </div>

      {/* Status text */}
      <div className="text-center">
        <motion.p
          className="text-jarvis-text-bright text-lg font-light tracking-widest uppercase mb-2"
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          JARVIS
        </motion.p>
        <p className="text-jarvis-text-dim text-sm font-mono">
          {status === 'loading' ? 'Initialising systems...' : 'Reconnecting...'}
        </p>
        {retryCount > 0 && (
          <p className="text-jarvis-text-dim text-xs mt-2 font-mono">
            Attempt {retryCount + 1}
          </p>
        )}
      </div>

      {/* Grid scan line effect */}
      <div className="w-48 h-px bg-jarvis-border relative overflow-hidden">
        <motion.div
          className="absolute inset-y-0 w-12 bg-gradient-to-r from-transparent via-jarvis-cyan to-transparent"
          animate={{ x: [-48, 192] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
        />
      </div>
    </div>
  );
}
