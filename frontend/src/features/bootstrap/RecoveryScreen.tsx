import { m } from 'framer-motion';
import { useBootstrapStore } from './bootstrapStore';

interface Props {
  error: string;
  retryCount: number;
}

export function RecoveryScreen({ error, retryCount }: Props) {
  const { reset } = useBootstrapStore();

  return (
    <div className="w-full h-full flex items-center justify-center bg-jarvis-bg">
      <m.div
        className="jarvis-panel max-w-lg w-full mx-6 p-8 text-center"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        {/* Warning icon */}
        <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center rounded-full border-2 border-jarvis-red">
          <span className="text-jarvis-red text-2xl font-bold">!</span>
        </div>

        <h2 className="text-jarvis-text-bright text-xl font-semibold mb-2 tracking-wide">
          Backend Unreachable
        </h2>
        <p className="text-jarvis-text-dim text-sm mb-6 leading-relaxed">
          JARVIS cannot connect to the backend gateway. Ensure the backend is running
          on <code className="text-jarvis-cyan text-xs">http://localhost:8000</code>.
        </p>

        {/* Error details */}
        <div className="bg-jarvis-bg-2 rounded border border-jarvis-border p-3 mb-6 text-left">
          <p className="text-jarvis-text-dim text-xs font-mono mb-1">Error:</p>
          <p className="text-jarvis-red text-xs font-mono break-all">{error}</p>
        </div>

        {/* Quick start hint */}
        <div className="bg-jarvis-bg-2 rounded border border-jarvis-border p-3 mb-6 text-left">
          <p className="text-jarvis-text-dim text-xs font-mono mb-2">Quick start:</p>
          <pre className="text-jarvis-cyan text-xs font-mono">make dev</pre>
        </div>

        <p className="text-jarvis-text-dim text-xs mb-6">
          {retryCount} reconnection {retryCount === 1 ? 'attempt' : 'attempts'} made.
        </p>

        <div className="flex gap-3 justify-center">
          <button
            className="btn-cockpit-primary px-6 py-2 text-sm"
            onClick={reset}
          >
            Retry
          </button>
          <button
            className="btn-cockpit px-6 py-2 text-sm"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      </m.div>
    </div>
  );
}
