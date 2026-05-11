import type { GPUWorkloads, WorkloadDevice } from '@/lib/api/types';
import { GlassPanel } from '@/components/ui/GlassPanel';

const WORKLOAD_LABELS: Record<keyof GPUWorkloads, string> = {
  localLlm:        'Local LLM',
  stt:             'STT / Whisper',
  tts:             'TTS',
  embeddings:      'Embeddings',
  faiss:           'FAISS Search',
  vision:          'Vision',
  rag:             'RAG',
  memorySynthesis: 'Memory Synth',
};

const DEVICE_COLOR: Record<WorkloadDevice, string> = {
  gpu:      'text-jarvis-green',
  cpu:      'text-jarvis-text-dim',
  cloud:    'text-jarvis-blue',
  disabled: 'text-jarvis-border',
};

const DEVICE_LABEL: Record<WorkloadDevice, string> = {
  gpu:      'GPU',
  cpu:      'CPU',
  cloud:    'Cloud',
  disabled: 'Off',
};

interface Props {
  workloads: GPUWorkloads;
}

export function GpuWorkloadsPanel({ workloads }: Props) {
  return (
    <GlassPanel className="p-4">
      <p className="text-jarvis-text-dim text-xs font-mono mb-3">Workload Device Routing</p>
      <div className="grid grid-cols-2 gap-2">
        {(Object.keys(WORKLOAD_LABELS) as (keyof GPUWorkloads)[]).map((key) => {
          const device = workloads[key];
          return (
            <div key={key} className="flex items-center justify-between py-1 border-b border-jarvis-border last:border-0">
              <span className="text-jarvis-text text-xs">{WORKLOAD_LABELS[key]}</span>
              <span className={`text-xs font-mono font-medium ${DEVICE_COLOR[device]}`}>
                {DEVICE_LABEL[device]}
              </span>
            </div>
          );
        })}
      </div>
    </GlassPanel>
  );
}
