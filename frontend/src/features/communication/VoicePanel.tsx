import { useCallback, useRef, useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { m, AnimatePresence } from 'framer-motion';
import { apiClient } from '@/lib/api/client';
import { env, apiUrl } from '@/lib/config/env';
import { generateRequestId, getSessionId } from '@/lib/session/session';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';
import {
  Mic,
  MicOff,
  Volume2,
  Ear,
  Radio,
  Activity,
  Zap,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Circle,
  Pause,
  Play,
  Upload,
  Globe,
  Cpu,
} from 'lucide-react';

type RecordState = 'idle' | 'recording' | 'processing' | 'done' | 'error';
type Lang = 'auto' | 'mn' | 'en';
type TtsLang = 'mn' | 'en';

interface VoiceStatus {
  stt: {
    enabled: boolean;
    available: boolean;
    engine: string;
    device: string;
    models?: { mn: string; en: string };
    loaded?: boolean;
  };
  tts: {
    enabled: boolean;
    available: boolean;
    engine: string;
    device: string;
    model?: string;
    sampleRate?: number;
    loaded?: boolean;
    voiceRefs?: { en: boolean; mn: boolean };
  };
}

// ─── Audio Visualizer ───────────────────────────────────────────────────────

function AudioVisualizer({ isActive, isPlaying }: { isActive: boolean; isPlaying: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const barCount = 32;
    const barWidth = W / barCount - 2;

    const draw = () => {
      ctx.clearRect(0, 0, W, H);

      for (let i = 0; i < barCount; i++) {
        let height: number;
        if (isActive) {
          // Simulate audio levels with sine waves
          const now = Date.now() / 300;
          height = Math.max(2, Math.sin(now + i * 0.4) * 0.5 + 0.5) * H * 0.7;
          height += Math.max(0, Math.sin(now * 0.7 + i * 0.7)) * H * 0.3;
        } else if (isPlaying) {
          // Gentle playback visualization
          const now = Date.now() / 500;
          height = Math.max(2, Math.sin(now + i * 0.2) * 0.3 + 0.5) * H * 0.4;
        } else {
          height = 2;
        }

        const x = i * (barWidth + 2) + 1;
        const y = H - height;

        const gradient = ctx.createLinearGradient(0, y, 0, H);
        if (isActive) {
          gradient.addColorStop(0, 'rgba(0, 229, 255, 0.9)');
          gradient.addColorStop(1, 'rgba(0, 102, 255, 0.3)');
        } else if (isPlaying) {
          gradient.addColorStop(0, 'rgba(0, 255, 136, 0.8)');
          gradient.addColorStop(1, 'rgba(0, 255, 136, 0.2)');
        } else {
          gradient.addColorStop(0, 'rgba(90, 122, 158, 0.2)');
          gradient.addColorStop(1, 'rgba(90, 122, 158, 0.05)');
        }

        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth, height);
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [isActive, isPlaying]);

  return (
    <canvas
      ref={canvasRef}
      width={260}
      height={60}
      className="w-full h-12 rounded-lg"
    />
  );
}

// ─── Command Card ────────────────────────────────────────────────────────────

interface VoiceCommand {
  phrase: string;
  action: string;
  icon: React.ReactNode;
}

const VOICE_COMMANDS: VoiceCommand[] = [
  { phrase: '"Hey JARVIS"', action: 'Wake / Activate', icon: <Zap size={10} /> },
  { phrase: '"Open chat"', action: 'Navigate to Chat', icon: <Mic size={10} /> },
  { phrase: '"Show GPU"', action: 'GPU Dashboard', icon: <Activity size={10} /> },
  { phrase: '"Run code"', action: 'Open Terminal', icon: <Radio size={10} /> },
  { phrase: '"Search for..."', action: 'Web Search', icon: <Ear size={10} /> },
  { phrase: '"Stop listening"', action: 'Deactivate', icon: <MicOff size={10} /> },
];

export function VoicePanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  // ── Bootstrap GPU data for STT device info (Merge: GPU → Voice) ──
  const bootstrap = useBootstrapStore((s) => s.data);
  const gpuInfo = bootstrap?.gpu;

  const { data: status } = useQuery<VoiceStatus>({
    queryKey: ['voice-status'],
    queryFn: () => apiClient.get<VoiceStatus>('/voice/status'),
    enabled: bootstrapReady,
    ...freshness.resourceState,
  });

  const [recordState, setRecordState] = useState<RecordState>('idle');
  const [transcript, setTranscript] = useState('');
  const [detectedLang, setDetectedLang] = useState<string | null>(null);
  const [ttsText, setTtsText] = useState('');
  const [ttsStatus, setTtsStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  // ── Language selectors ──────────────────────────────────────────────────
  const [sttLang, setSttLang] = useState<Lang>('auto');
  const [ttsLang, setTtsLang] = useState<TtsLang>('en');

  // ── Voice ref upload ────────────────────────────────────────────────────
  const [refLang, setRefLang] = useState<TtsLang>('en');
  const [refUploadStatus, setRefUploadStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle');
  const refInputRef = useRef<HTMLInputElement>(null);

  // ── Audio refs for TTS playback ──────────────────────────────────────────
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => stopAudio();
  }, [stopAudio]);

  // ── Wake word state ──────────────────────────────────────────────────────
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [isWaken, setIsWaken] = useState(false);
  const [wakeWordDetected, setWakeWordDetected] = useState(false);
  const [interruptionMode, setInterruptionMode] = useState(true);
  const [pushToTalk, setPushToTalk] = useState(true);

  // Simulated wake word detection listener
  const wakeWordRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  // ── Simulated wake word detection ────────────────────────────────────────
  useEffect(() => {
    if (!wakeWordEnabled) {
      if (wakeWordRef.current) clearInterval(wakeWordRef.current);
      return;
    }

    // Simulated audio level monitoring
    wakeWordRef.current = setInterval(() => {
      setAudioLevel(Math.random());
    }, 200);

    return () => {
      if (wakeWordRef.current) clearInterval(wakeWordRef.current);
    };
  }, [wakeWordEnabled]);

  const handleWakeWordToggle = () => {
    setWakeWordEnabled(!wakeWordEnabled);
    if (wakeWordEnabled) {
      setIsWaken(false);
      setWakeWordDetected(false);
    }
  };

  const handleWakeAction = () => {
    setIsWaken(!isWaken);
    if (!isWaken) {
      setWakeWordDetected(true);
      setTimeout(() => setWakeWordDetected(false), 2000);
      // Simulate wake word detection
      setTimeout(() => {
        setTranscript('J.A.R.V.I.S. online — how can I assist you?');
      }, 500);
    }
  };

  // ── Recording ──────────────────────────────────────────────────────────────
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
        form.append('lang', sttLang);
        try {
          const res = await apiClient.postForm<{ transcript: string; language: string }>('/voice/stt', form);
          setTranscript(res.transcript ?? '');
          setDetectedLang(res.language ?? null);
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

  // ── TTS with interruption ─────────────────────────────────────────────────
  const speakMut = useMutation({
    mutationFn: async (text: string) => {
      const url = apiUrl('/voice/tts');
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': generateRequestId(),
          'X-Session-ID': getSessionId(),
          'X-Client-Version': env.clientVersion,
        },
        body: JSON.stringify({ text, lang: ttsLang, interruptPrevious: interruptionMode }),
      });

      if (!response.ok) {
        if (response.status === 204) {
          throw new Error('TTS engine not available');
        }
        throw new Error(`TTS failed (HTTP ${response.status})`);
      }

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      audioUrlRef.current = blobUrl;

      const audio = new Audio(blobUrl);
      audioRef.current = audio;

      return new Promise<void>((resolve, reject) => {
        audio.onended = () => {
          stopAudio();
          resolve();
        };
        audio.onerror = () => {
          stopAudio();
          reject(new Error('Audio playback failed'));
        };
        audio.play().catch(reject);
      });
    },
    onSuccess: () => setTtsStatus('done'),
    onError: () => {
      stopAudio();
      setTtsStatus('error');
    },
  });

  // ── Voice reference upload ────────────────────────────────────────────────
  const uploadVoiceRef = useCallback(async (file: File) => {
    setRefUploadStatus('uploading');
    try {
      const form = new FormData();
      form.append('audio', file, file.name);
      form.append('lang', refLang);
      await apiClient.postForm('/voice/set-ref', form);
      setRefUploadStatus('done');
      setTimeout(() => setRefUploadStatus('idle'), 3000);
    } catch {
      setRefUploadStatus('error');
      setTimeout(() => setRefUploadStatus('idle'), 4000);
    }
  }, [refLang]);

  const speakText = useCallback(async () => {
    if (!ttsText.trim()) return;
    stopAudio();
    speakMut.reset();
    setTtsStatus('loading');
    speakMut.mutate(ttsText);
  }, [ttsText, speakMut, stopAudio]);

  // Handle interruption — stop current TTS when starting new recording
  const handleInterruptAndRecord = useCallback(async () => {
    if (interruptionMode && (speakMut.isPending || audioRef.current)) {
      stopAudio();
      speakMut.reset();
      setTtsStatus('idle');
    }
    await startRecording();
  }, [interruptionMode, speakMut, startRecording, stopAudio]);

  const sttAvailable = status?.stt?.available ?? false;
  const ttsAvailable = status?.tts?.available ?? false;

  const isRecording = recordState === 'recording';
  const isPlaying = ttsStatus === 'loading';

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader
        title="Voice"
        subtitle="Speech-to-text, text-to-speech, wake word, and interruption handling"
      />

      {/* ── Status Bar ── */}
      <GlassPanel className="p-4 mb-4">
        <div className="flex items-center gap-4 flex-wrap">
          <StatusDot
            status={sttAvailable ? 'online' : 'offline'}
            label={`STT: ${sttAvailable ? 'ready' : 'unavailable'}`}
          />
          <StatusDot
            status={ttsAvailable ? 'online' : 'offline'}
            label={`TTS: ${ttsAvailable ? 'ready' : 'unavailable'}`}
          />
          {/* GPU device indicator (Merge 3: GPU → Voice) */}
          {gpuInfo && gpuInfo.cudaAvailable && (
            <StatusDot
              status="online"
              label={`GPU: ${gpuInfo.activeDevice ?? 'N/A'}`}
            />
          )}
          <NeonBadge
            color={wakeWordEnabled ? 'cyan' : 'dim'}
            label={wakeWordEnabled ? 'WAKE WORD' : 'WAKE OFF'}
            size="sm"
            pulse={wakeWordEnabled}
          />
          <NeonBadge
            color={interruptionMode ? 'green' : 'yellow'}
            label={interruptionMode ? 'INTERRUPT ON' : 'INTERRUPT OFF'}
            size="sm"
          />
          {isWaken && (
            <NeonBadge color="green" label="LISTENING" size="sm" pulse />
          )}
        </div>
      </GlassPanel>

      {/* ── GPU Compute info (Merge 3: GPU → Voice) ── */}
      {gpuInfo && gpuInfo.cudaAvailable && (
        <GlassPanel className="p-3 mb-4">
          <div className="flex items-center gap-3 text-xs font-mono">
            <Cpu size={14} className="text-jarvis-purple" />
            <span className="text-jarvis-text-dim/70">STT Backend:</span>
            <span className="text-jarvis-text-bright">{gpuInfo.activeDevice ?? 'GPU'}</span>
            <span className="text-jarvis-text-dim/30 mx-1">|</span>
            <span className="text-jarvis-text-dim/70">VRAM:</span>
            <span className="text-jarvis-text-bright">
              {gpuInfo.vram.usedMb > 1024 ? `${(gpuInfo.vram.usedMb / 1024).toFixed(1)}G` : `${gpuInfo.vram.usedMb.toFixed(0)}M`}
              {' / '}
              {gpuInfo.vram.totalMb > 1024 ? `${(gpuInfo.vram.totalMb / 1024).toFixed(1)}G` : `${gpuInfo.vram.totalMb.toFixed(0)}M`}
            </span>
            <div className="flex-1" />
            <NeonBadge color="purple" size="sm" label="GPU ACCELERATED" />
          </div>
        </GlassPanel>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ── STT Panel ── */}
        <GlassPanel className="p-5" glow>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Mic size={14} className={sttAvailable ? 'text-jarvis-cyan' : 'text-jarvis-text-dim'} />
              <p className="text-jarvis-text-bright text-sm font-mono font-semibold">Speech → Text</p>
            </div>
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
              {status.stt.models && (
                <>
                  <span className="text-jarvis-text-dim">MN model</span>
                  <span className="text-jarvis-text-bright truncate" title={status.stt.models.mn}>
                    {status.stt.models.mn.split('/').pop()}
                  </span>
                  <span className="text-jarvis-text-dim">EN model</span>
                  <span className="text-jarvis-text-bright truncate" title={status.stt.models.en}>
                    {status.stt.models.en.split('/').pop()}
                  </span>
                </>
              )}
              <span className="text-jarvis-text-dim">Loaded</span>
              <span className={status.stt.loaded ? 'text-jarvis-green' : 'text-jarvis-yellow'}>
                {status.stt.loaded ? 'yes' : 'lazy (loads on first use)'}
              </span>
            </div>
          )}

          {sttAvailable ? (
            <div className="space-y-4">
              {/* Language selector */}
              <div className="flex items-center gap-2">
                <Globe size={12} className="text-jarvis-text-dim shrink-0" />
                <span className="text-[11px] font-mono text-jarvis-text-dim">Language:</span>
                {(['auto', 'mn', 'en'] as Lang[]).map((l) => (
                  <button
                    key={l}
                    onClick={() => setSttLang(l)}
                    className={`px-2.5 py-1 text-[10px] font-mono rounded border transition-colors ${
                      sttLang === l
                        ? 'border-jarvis-cyan/60 text-jarvis-cyan bg-jarvis-cyan/10'
                        : 'border-jarvis-border/30 text-jarvis-text-dim hover:text-jarvis-cyan hover:border-jarvis-cyan/30'
                    }`}
                  >
                    {l === 'auto' ? 'Auto' : l === 'mn' ? 'Монгол' : 'English'}
                  </button>
                ))}
              </div>

              {/* Voice activity visualizer */}
              <div className="bg-jarvis-bg rounded-lg border border-jarvis-border/30 p-2">
                <AudioVisualizer isActive={isRecording} isPlaying={false} />
              </div>

              <div className="flex gap-2">
                {!isRecording ? (
                  <button
                    className="btn-cockpit-primary px-4 py-2 text-sm flex-1 flex items-center justify-center gap-2"
                    onClick={interruptionMode && speakMut.isPending ? handleInterruptAndRecord : startRecording}
                    disabled={recordState === 'processing'}
                  >
                    {recordState === 'processing' ? (
                      <><Loader2 size={14} className="animate-spin" /> Transcribing…</>
                    ) : (
                      <><Mic size={14} /> Record</>
                    )}
                  </button>
                ) : (
                  <button
                    className="px-4 py-2 text-sm flex-1 rounded-lg border border-jarvis-red text-jarvis-red bg-jarvis-red/5 flex items-center justify-center gap-2 transition-all duration-200 hover:bg-jarvis-red/10"
                    onClick={stopRecording}
                  >
                    <span className="w-2 h-2 rounded-full bg-jarvis-red animate-pulse" />
                    Stop Recording
                  </button>
                )}

                {pushToTalk && (
                  <button
                    onMouseDown={startRecording}
                    onMouseUp={stopRecording}
                    onMouseLeave={stopRecording}
                    className="px-3 py-2 text-xs font-mono rounded-lg border border-jarvis-cyan/40 text-jarvis-cyan bg-jarvis-cyan/5 hover:bg-jarvis-cyan/10 transition-all flex items-center gap-1.5"
                  >
                    <Radio size={12} />
                    Hold
                  </button>
                )}
              </div>

              {/* Recording indicator */}
              <AnimatePresence>
                {isRecording && (
                  <m.div
                    className="flex items-center gap-2 text-jarvis-red text-xs font-mono"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <span className="w-2 h-2 rounded-full bg-jarvis-red animate-pulse" />
                    Recording — speak now
                  </m.div>
                )}
              </AnimatePresence>

              {/* Wake word status */}
              {wakeWordEnabled && (
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-jarvis-bg border border-jarvis-border/20">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${isWaken ? 'bg-jarvis-green animate-pulse' : 'bg-jarvis-text-dim'}`} />
                    <span className="text-xs font-mono text-jarvis-text-dim">
                      {isWaken ? 'Wake word active — listening' : 'Awaiting wake word…'}
                    </span>
                  </div>
                  <button
                    onClick={handleWakeAction}
                    className="text-[10px] font-mono px-2 py-1 rounded border border-jarvis-border/30 text-jarvis-cyan/60 hover:text-jarvis-cyan transition-colors"
                  >
                    {isWaken ? 'Deactivate' : 'Simulate wake'}
                  </button>
                </div>
              )}

              {/* Wake word detected flash */}
              <AnimatePresence>
                {wakeWordDetected && (
                  <m.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="p-3 rounded-lg bg-jarvis-green/10 border border-jarvis-green/30 text-center"
                  >
                    <p className="text-jarvis-green text-xs font-mono flex items-center justify-center gap-2">
                      <Zap size={12} /> "Hey JARVIS" detected — activating
                    </p>
                  </m.div>
                )}
              </AnimatePresence>

              {/* Transcript output */}
              {transcript && (
                <div className="bg-jarvis-bg border border-jarvis-border rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <CheckCircle2 size={10} className="text-jarvis-green" />
                    <p className="text-jarvis-text-dim text-[10px] font-mono">Transcript:</p>
                    {detectedLang && (
                      <span className="ml-auto text-[10px] font-mono text-jarvis-cyan/70">
                        detected: {detectedLang === 'mn' ? 'Монгол' : 'English'}
                      </span>
                    )}
                  </div>
                  <p className="text-jarvis-text-bright text-sm font-mono whitespace-pre-wrap">{transcript}</p>
                </div>
              )}

              {recordState === 'error' && (
                <div className="flex items-center gap-2 text-jarvis-red text-xs font-mono p-2 rounded-lg bg-jarvis-red/5 border border-jarvis-red/20">
                  <AlertTriangle size={12} />
                  {errorMsg}
                </div>
              )}
            </div>
          ) : (
            <UnavailableNote feature="STT" pkg="transformers accelerate" />
          )}
        </GlassPanel>

        {/* ── TTS Panel ── */}
        <GlassPanel className="p-5" glow>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Volume2 size={14} className={ttsAvailable ? 'text-jarvis-green' : 'text-jarvis-text-dim'} />
              <p className="text-jarvis-text-bright text-sm font-mono font-semibold">Text → Speech</p>
            </div>
            <StatusDot
              status={ttsAvailable ? 'online' : 'offline'}
              label={ttsAvailable ? 'ready' : 'unavailable'}
            />
          </div>

          {ttsAvailable ? (
            <div className="space-y-4">
              {/* TTS engine info */}
              {status?.tts && (
                <div className="grid grid-cols-2 gap-1 text-xs font-mono">
                  <span className="text-jarvis-text-dim">Engine</span>
                  <span className="text-jarvis-text-bright">{status.tts.engine}</span>
                  {status.tts.model && (
                    <>
                      <span className="text-jarvis-text-dim">Model</span>
                      <span className="text-jarvis-text-bright truncate" title={status.tts.model}>
                        {status.tts.model.split('/').pop()}
                      </span>
                    </>
                  )}
                  {status.tts.sampleRate && (
                    <>
                      <span className="text-jarvis-text-dim">Sample rate</span>
                      <span className="text-jarvis-text-bright">{status.tts.sampleRate} Hz</span>
                    </>
                  )}
                  {status.tts.voiceRefs && (
                    <>
                      <span className="text-jarvis-text-dim">Voice refs</span>
                      <span className="text-jarvis-text-bright">
                        EN: {status.tts.voiceRefs.en ? '✓' : '—'} | MN: {status.tts.voiceRefs.mn ? '✓' : '—'}
                      </span>
                    </>
                  )}
                </div>
              )}

              {/* Language selector */}
              <div className="flex items-center gap-2">
                <Globe size={12} className="text-jarvis-text-dim shrink-0" />
                <span className="text-[11px] font-mono text-jarvis-text-dim">Language:</span>
                {(['en', 'mn'] as TtsLang[]).map((l) => (
                  <button
                    key={l}
                    onClick={() => setTtsLang(l)}
                    className={`px-2.5 py-1 text-[10px] font-mono rounded border transition-colors ${
                      ttsLang === l
                        ? 'border-jarvis-green/60 text-jarvis-green bg-jarvis-green/10'
                        : 'border-jarvis-border/30 text-jarvis-text-dim hover:text-jarvis-green hover:border-jarvis-green/30'
                    }`}
                  >
                    {l === 'mn' ? 'Монгол' : 'English'}
                  </button>
                ))}
              </div>

              {/* Playback visualizer */}
              <div className="bg-jarvis-bg rounded-lg border border-jarvis-border/30 p-2">
                <AudioVisualizer isActive={false} isPlaying={isPlaying} />
              </div>

              {/* Interruption mode toggle */}
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-jarvis-bg border border-jarvis-border/20">
                <div className="flex items-center gap-2">
                  <Zap size={12} className={interruptionMode ? 'text-jarvis-green' : 'text-jarvis-text-dim'} />
                  <span className="text-xs font-mono text-jarvis-text-dim">
                    Interruption mode
                  </span>
                </div>
                <button
                  onClick={() => setInterruptionMode(!interruptionMode)}
                  className={`text-[10px] font-mono px-2 py-1 rounded border transition-colors ${
                    interruptionMode
                      ? 'border-jarvis-green/30 text-jarvis-green bg-jarvis-green/5'
                      : 'border-jarvis-border/30 text-jarvis-text-dim'
                  }`}
                >
                  {interruptionMode ? 'On' : 'Off'}
                </button>
              </div>

              <textarea
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                rows={4}
                placeholder="Enter text to synthesise…"
                className="w-full resize-none bg-jarvis-bg border border-jarvis-border rounded-lg px-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim focus:outline-none focus:border-jarvis-cyan/60 transition-colors"
              />

              <div className="flex gap-2">
                <button
                  className="btn-cockpit-primary px-4 py-2 text-sm flex-1 flex items-center justify-center gap-2"
                  onClick={speakText}
                  disabled={!ttsText.trim() || ttsStatus === 'loading'}
                >
                  {ttsStatus === 'loading' ? (
                    <><Loader2 size={14} className="animate-spin" /> Synthesising…</>
                  ) : (
                    <><Play size={14} /> Speak</>
                  )}
                </button>
                {interruptionMode && isPlaying && (
                  <button
                    onClick={() => { stopAudio(); speakMut.reset(); setTtsStatus('idle'); }}
                    className="px-3 py-2 rounded-lg border border-jarvis-red/40 text-jarvis-red bg-jarvis-red/5 hover:bg-jarvis-red/10 transition-all text-xs font-mono flex items-center gap-1"
                  >
                    <Pause size={12} />
                    Stop
                  </button>
                )}
              </div>

              <AnimatePresence>
                {ttsStatus === 'done' && (
                  <m.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-2 text-jarvis-green text-xs font-mono"
                  >
                    <CheckCircle2 size={12} />
                    Audio playback complete.
                  </m.div>
                )}
                {ttsStatus === 'error' && (
                  <m.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-2 text-jarvis-red text-xs font-mono"
                  >
                    <AlertTriangle size={12} />
                    TTS request failed.
                  </m.div>
                )}
              </AnimatePresence>

              {/* Voice Reference Upload */}
              <div className="border-t border-jarvis-border/20 pt-4">
                <p className="text-[11px] font-mono text-jarvis-text-dim mb-2 flex items-center gap-1.5">
                  <Upload size={10} />
                  Voice Clone Reference (WAV, ≥3s)
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                  {(['en', 'mn'] as TtsLang[]).map((l) => (
                    <button
                      key={l}
                      onClick={() => setRefLang(l)}
                      className={`px-2 py-1 text-[10px] font-mono rounded border transition-colors ${
                        refLang === l
                          ? 'border-jarvis-purple/60 text-jarvis-purple bg-jarvis-purple/10'
                          : 'border-jarvis-border/30 text-jarvis-text-dim hover:border-jarvis-purple/40'
                      }`}
                    >
                      {l === 'mn' ? 'Монгол' : 'English'}
                    </button>
                  ))}
                  <button
                    onClick={() => refInputRef.current?.click()}
                    disabled={refUploadStatus === 'uploading'}
                    className="px-3 py-1 text-[10px] font-mono rounded border border-jarvis-purple/40 text-jarvis-purple bg-jarvis-purple/5 hover:bg-jarvis-purple/10 transition-all flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {refUploadStatus === 'uploading' ? (
                      <><Loader2 size={10} className="animate-spin" /> Uploading…</>
                    ) : refUploadStatus === 'done' ? (
                      <><CheckCircle2 size={10} /> Uploaded</>
                    ) : refUploadStatus === 'error' ? (
                      <><AlertTriangle size={10} /> Failed</>
                    ) : (
                      <><Upload size={10} /> Upload {refLang.toUpperCase()} ref</>
                    )}
                  </button>
                  <input
                    ref={refInputRef}
                    type="file"
                    accept="audio/wav,audio/*"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) uploadVoiceRef(f);
                      e.target.value = '';
                    }}
                  />
                </div>
              </div>
            </div>
          ) : (
            <UnavailableNote feature="TTS" pkg="transformers soundfile" />
          )}
        </GlassPanel>
      </div>

      {/* ── Wake Word & Voice Commands Section ── */}
      <GlassPanel className="p-5 mt-4" glow>
        <div className="flex items-center gap-2 mb-4">
          <Ear size={14} className="text-jarvis-purple" />
          <span className="text-jarvis-text-bright text-xs font-mono font-semibold tracking-wider uppercase">
            Wake Word & Voice Commands
          </span>
          <NeonBadge
            color={wakeWordEnabled ? 'green' : 'dim'}
            label={wakeWordEnabled ? 'ACTIVE' : 'DISABLED'}
            size="sm"
            pulse={wakeWordEnabled}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Wake Word Settings */}
          <div className="space-y-3">
            <p className="text-jarvis-text-dim text-[11px] font-mono">Settings</p>

            <div className="flex items-center justify-between p-3 rounded-lg bg-jarvis-bg border border-jarvis-border/20">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-jarvis-cyan/60" />
                <span className="text-xs font-mono text-jarvis-text-dim">Wake word</span>
              </div>
              <span className="text-xs font-mono text-jarvis-cyan">"Hey JARVIS"</span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-jarvis-bg border border-jarvis-border/20">
              <div className="flex items-center gap-2">
                <Radio size={12} className="text-jarvis-text-dim" />
                <span className="text-xs font-mono text-jarvis-text-dim">Push-to-talk</span>
              </div>
              <button
                onClick={() => setPushToTalk(!pushToTalk)}
                className={`text-[10px] font-mono px-2 py-1 rounded border transition-colors ${
                  pushToTalk
                    ? 'border-jarvis-cyan/30 text-jarvis-cyan bg-jarvis-cyan/5'
                    : 'border-jarvis-border/30 text-jarvis-text-dim'
                }`}
              >
                {pushToTalk ? 'On' : 'Off'}
              </button>
            </div>

            <button
              onClick={handleWakeWordToggle}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-jarvis-border/30 text-jarvis-text-dim hover:text-jarvis-cyan hover:border-jarvis-cyan/40 transition-all duration-200"
            >
              {wakeWordEnabled ? 'Disable wake word' : 'Enable wake word'}
            </button>
          </div>

          {/* Voice Commands */}
          <div>
            <p className="text-jarvis-text-dim text-[11px] font-mono mb-2">Available Commands</p>
            <div className="space-y-1.5">
              {VOICE_COMMANDS.map((cmd, i) => (
                <m.div
                  key={cmd.phrase}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-3 p-2.5 rounded-lg bg-jarvis-bg/60 border border-jarvis-border/20 hover:border-jarvis-cyan/20 transition-all duration-200 cursor-default"
                >
                  <span className="text-jarvis-cyan/60 shrink-0">{cmd.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono text-jarvis-cyan/80">{cmd.phrase}</p>
                    <p className="text-[10px] font-mono text-jarvis-text-dim/60">{cmd.action}</p>
                  </div>
                </m.div>
              ))}
            </div>
          </div>
        </div>
      </GlassPanel>

      {/* ── Status Footer ── */}
      <GlassPanel className="p-3 mt-4">
        <div className="flex items-center justify-center gap-4 text-[10px] font-mono text-jarvis-text-dim/40">
          <span className="flex items-center gap-1">
            <Circle size={6} className={isWaken ? 'text-jarvis-green' : 'text-jarvis-text-dim'} />
            {isWaken ? 'Active' : 'Standby'}
          </span>
          <span>|</span>
          <span>Audio level: {(audioLevel * 100).toFixed(0)}%</span>
          <span>|</span>
          <span>Wake: {wakeWordEnabled ? 'On' : 'Off'}</span>
          <span>|</span>
          <span>Interrupt: {interruptionMode ? 'On' : 'Off'}</span>
        </div>
      </GlassPanel>
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
