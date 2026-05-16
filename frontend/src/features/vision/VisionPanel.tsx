import React, { useState, useRef, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface VisionStatus {
  enabled: boolean;
  providerSupportsVision: boolean;
  maxImageSizeMb: number;
}

interface VisionResult {
  description: string;
  model: string;
  providerId: string;
  imageSize: number;
  contentType: string;
}

export function VisionPanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const [dragOver, setDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('Describe this image in detail.');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: status } = useQuery<VisionStatus>({
    queryKey: ['vision-status'],
    queryFn: () => apiClient.get<VisionStatus>('/vision/status'),
    enabled: bootstrapReady,
    ...freshness.resourceState,
  });

  const analyzeMut = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append('image', file);
      return apiClient.postForm<VisionResult>('/vision/analyze', form);
    },
  });

  const handleFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) return;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    analyzeMut.mutate(file);
  }, [analyzeMut]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const ready = status?.enabled && status?.providerSupportsVision;

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="Vision" subtitle="Image analysis via active AI provider" />

      {status && (
        <GlassPanel className="p-4 mt-6 mb-4">
          <div className="flex items-center gap-4 flex-wrap">
            <StatusDot status={ready ? 'online' : 'offline'} label={ready ? 'ready' : status.enabled ? 'provider lacks vision' : 'disabled'} />
            <span className="text-jarvis-text-dim text-xs font-mono">max size: {status.maxImageSizeMb} MB</span>
          </div>
        </GlassPanel>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Upload zone */}
        <div>
          <GlassPanel className="p-5 mb-3">
            <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Prompt</p>
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="w-full bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-xs font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60"
            />
          </GlassPanel>

          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={[
              'jarvis-panel rounded-lg p-8 text-center cursor-pointer transition-colors border-2 border-dashed',
              dragOver ? 'border-jarvis-cyan/60 bg-jarvis-cyan/5' : 'border-jarvis-border hover:border-jarvis-cyan/30',
            ].join(' ')}
          >
            <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={onFileChange} />
            {previewUrl ? (
              <img src={previewUrl} alt="preview" className="max-h-40 mx-auto rounded object-contain mb-2" />
            ) : (
              <p className="text-jarvis-text-dim text-xs font-mono">
                Drop an image here or click to upload
              </p>
            )}
            {analyzeMut.isPending && (
              <p className="text-jarvis-cyan text-xs font-mono mt-2 animate-pulse">Analyzing…</p>
            )}
          </div>
        </div>

        {/* Result */}
        <GlassPanel className="p-5">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Analysis</p>
          {analyzeMut.isSuccess && analyzeMut.data ? (
            <div>
              <p className="text-jarvis-text-bright text-xs font-mono leading-relaxed whitespace-pre-wrap mb-4">
                {analyzeMut.data.description}
              </p>
              <div className="border-t border-jarvis-border pt-3 space-y-1">
                <p className="text-jarvis-text-dim text-xs font-mono">model: {analyzeMut.data.model}</p>
                <p className="text-jarvis-text-dim text-xs font-mono">provider: {analyzeMut.data.providerId}</p>
                <p className="text-jarvis-text-dim text-xs font-mono">
                  size: {(analyzeMut.data.imageSize / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
          ) : analyzeMut.isError ? (
            <p className="text-jarvis-red text-xs font-mono">
              Analysis failed. Ensure the active provider supports vision.
            </p>
          ) : (
            <p className="text-jarvis-text-dim text-xs font-mono">Upload an image to see the analysis here.</p>
          )}
        </GlassPanel>
      </div>
    </div>
  );
}
