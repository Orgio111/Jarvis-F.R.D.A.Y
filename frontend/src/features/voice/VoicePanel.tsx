import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

type RecordState = 'idle' | 'recording' | 'processing' | 'done' | 'error';

interface VoiceStatus {
  stt: { enabled: boolean; available: boolean; engine: string; device: string; modelSize: string };
  tts: { enabled: boolean; available: boolean; engine: string; device: string };
}

export function VoicePanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const { data: status } = useQuery<VoiceStatus>({
    queryKey: ['voice-status'],
    queryFn: () => apiClient.get<VoiceStatus>('/voice/status'),
    enabled: bootstrapReady,
    staleTime: 30_000,
  });

  const [recordState, setRecordState] = useState<RecordState>('idle');
  const [transcript, setTranscript] = useState('');
  const [ttsText, setTtsText] = useState('');
  const [ttsStatus, setTtsStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    setTranscript('');
    setErrorMsg('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecordState('processing');
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const form = new FormData();
        form.append('audio', blob, 'recording.webm');
        try {
          const res = await apiClient.postForm<{ transcript: string }>('/voice/stt', form);
          setTranscript(res.transcript ?? '');
          setRecordState('done');
        } catch (err) {
          setErrorMsg(err instanceof Error ? err.message : 'STT failed');
          setRecordState('error');
        }
      };
      mr.start();
      mediaRef.current = mr;
      setRecordState('recording');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Microphone access denied');
      setRecordState('error');
    }
  }, []);

  const stopRecording = useCallback(() => {
    mediaRef.current?.stop();
    mediaRef.current = null;
  }, []);

  const speakText = useCallback(async () => {
    if (!ttsText.trim()) return;
    setTtsStatus('loading');
    try {
      await apiClient.post('/voice/tts', { text: ttsText });
      setTtsStatus('done');
    } catch {
      setTtsStatus('error');
    }
  }, [ttsText]);

  const sttAvailable = status?.stt?.available ?? false;
  const ttsAvailable = status?.tts?.available ?? false;

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="Voice" subtitle="Speech-to-text and text-to-speech" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        {/* STT */}
        <GlassPanel className="p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-jarvis-text-bright text-sm font-mono font-semibold">Speech → Text</p>
            <StatusDot
              status={sttAvailable ? 'online' : 'offline'}
              label={sttAvailable ? 'ready' : 'unavailable'}
            />
          </div>

          {status?.stt && (
            <div className="grid grid-cols-2 gap-1 text-xs font-mono mb-4">
              <span className="text-jarvis-text-dim">Engine</span>
              <span className="text-jarvis-text-bright">{status.stt.engine}</span>
              <span className="text-jarvis-text-dim">Device</span>
              <span className="text-jarvis-text-bright">{status.stt.device}</span>
              <span className="text-jarvis-text-dim">Model</span>
              <span className="text-jarvis-text-bright">{status.stt.modelSize}</span>
            </div>
          )}

          {sttAvailable ? (
            <div className="space-y-3">
              <div className="flex gap-2">
                {recordState !== 'recording' ? (
                  <button
                    className="btn-cockpit-primary px-4 py-2 text-sm flex-1"
                    onClick={startRecording}
                    disabled={recordState === 'processing'}
                  >
                    {recordState === 'processing' ? 'Transcribing…' : '⏺ Record'}
                  </button>
                ) : (
                  <button
                    className="btn-cockpit px-4 py-2 text-sm flex-1 border-jarvis-red text-jarvis-red"
                    onClick={stopRecording}
                  >
                    ⏹ Stop
                  </button>
                )}
              </div>

              <AnimatePresence>
                {recordState === 'recording' && (
                  <motion.div
                    className="flex items-center gap-2 text-jarvis-red text-xs font-mono"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  >
                    <span className="w-2 h-2 rounded-full bg-jarvis-red animate-pulse" />
                    Recording…
                  </motion.div>
                )}
              </AnimatePresence>

              {transcript && (
                <div className="bg-jarvis-bg border border-jarvis-border rounded p-3">
                  <p className="text-jarvis-text-dim text-xs font-mono mb-1">Transcript:</p>
                  <p className="text-jarvis-text-bright text-sm font-mono whitespace-pre-wrap">{transcript}</p>
                </div>
              )}
              {recordState === 'error' && (
                <p className="text-jarvis-red text-xs font-mono">{errorMsg}</p>
              )}
            </div>
          ) : (
            <UnavailableNote feature="STT" pkg="faster-whisper" />
          )}
        </GlassPanel>

        {/* TTS */}
        <GlassPanel className="p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-jarvis-text-bright text-sm font-mono font-semibold">Text → Speech</p>
            <StatusDot
              status={ttsAvailable ? 'online' : 'offline'}
              label={ttsAvailable ? 'ready' : 'unavailable'}
            />
          </div>

          {ttsAvailable ? (
            <div className="space-y-3">
              <textarea
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                rows={4}
                placeholder="Enter text to synthesise…"
                className="w-full resize-none bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60"
              />
              <button
                className="btn-cockpit-primary px-4 py-2 text-sm w-full"
                onClick={speakText}
                disabled={!ttsText.trim() || ttsStatus === 'loading'}
              >
                {ttsStatus === 'loading' ? 'Synthesising…' : '▶ Speak'}
              </button>
              {ttsStatus === 'done' && (
                <p className="text-jarvis-cyan text-xs font-mono">Audio sent to backend.</p>
              )}
              {ttsStatus === 'error' && (
                <p className="text-jarvis-red text-xs font-mono">TTS request failed.</p>
              )}
            </div>
          ) : (
            <UnavailableNote feature="TTS" pkg="pyttsx3" />
          )}
        </GlassPanel>
      </div>
    </div>
  );
}

function UnavailableNote({ feature, pkg }: { feature: string; pkg: string }) {
  return (
    <div className="text-jarvis-text-dim text-xs font-mono space-y-1">
      <p>{feature} engine not available.</p>
      <p>
        Install with:{' '}
        <code className="text-jarvis-cyan">pip install {pkg}</code>
      </p>
    </div>
  );
}
