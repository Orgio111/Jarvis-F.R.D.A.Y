/**
 * Canonical frontend API types — mirrors the Go/Python contract exactly.
 */

// ─── Canonical response envelopes ──────────────────────────────────────────────

export interface ApiSuccess<T = unknown> {
  ok: true;
  data: T;
  correlationId: string;
  timestamp: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorEnvelope {
  ok: false;
  error: ApiErrorDetail;
  correlationId: string;
  timestamp: string;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiErrorEnvelope;

// ─── Canonical SSE / WebSocket event ──────────────────────────────────────────

export interface BackendEvent<TPayload = unknown> {
  id: string;
  type: string;
  version: string;
  timestamp: string;
  correlationId: string;
  requestId: string | null;
  sessionId: string | null;
  source: string;
  payload: TPayload;
}

// ─── GPU DTOs ──────────────────────────────────────────────────────────────────

export type WorkloadDevice = 'gpu' | 'cpu' | 'cloud' | 'disabled';

export interface GPUMemory {
  totalMb: number;
  usedMb: number;
  freeMb: number;
}

export interface GPUUtilization {
  gpuPercent: number;
  memoryPercent: number;
  temperatureC: number;
  powerWatts: number;
}

export interface GPUWorkloads {
  localLlm: WorkloadDevice;
  stt: WorkloadDevice;
  tts: WorkloadDevice;
  embeddings: WorkloadDevice;
  faiss: WorkloadDevice;
  vision: WorkloadDevice;
  rag: WorkloadDevice;
  memorySynthesis: WorkloadDevice;
}

export interface GPUFallback {
  cpuFallbackAllowed: boolean;
  cpuFallbackActive: boolean;
  reason: string | null;
}

export interface GPUStatus {
  enabled: boolean;
  available: boolean;
  required: boolean;
  provider: string;
  deviceCount: number;
  activeDevice: string;
  cudaAvailable: boolean;
  cudaVersion: string | null;
  driverVersion: string | null;
  vram: GPUMemory;
  utilization: GPUUtilization;
  workloads: GPUWorkloads;
  fallback: GPUFallback;
}

export interface GPUMetrics {
  timestamp: string;
  deviceIndex: number;
  deviceName: string;
  utilization: GPUUtilization;
  vram: GPUMemory;
}

export interface GPUSettings {
  enabled: boolean;
  required: boolean;
  allowCpuFallback: boolean;
  preferHalfPrecision: boolean;
  enableMixedPrecision: boolean;
  memorySoftLimitMb: number;
  memoryHardLimitMb: number;
}

// ─── Provider DTOs ────────────────────────────────────────────────────────────

export interface ProviderStatus {
  id: string;
  name: string;
  status: 'available' | 'provider_unavailable' | 'error' | 'checking';
  reason?: string;
  modelCount: number;
  deviceMode: 'cloud' | 'gpu' | 'cpu' | 'disabled';
  isDefault?: boolean;
  isFallback?: boolean;
  latencyMs?: number;
}

export interface ProvidersSummary {
  primary: ProviderStatus;
  fallback: ProviderStatus;
  available: ProviderStatus[];
}

// ─── Model DTOs ───────────────────────────────────────────────────────────────

export interface Model {
  id: string;
  name: string;
  providerId: string;
  providerName: string;
  groups: string[];
  contextWindow: number;
  maxTokens: number;
  supportsVision: boolean;
  supportsTools: boolean;
  deviceMode: 'cloud' | 'gpu' | 'cpu' | 'disabled';
  isDefault: boolean;
  isFree: boolean;
  description?: string;
}

export interface ModelsSummary {
  defaultChatModel: string;
  defaultCoderModel: string;
  defaultFastModel: string;
  totalAvailable: number;
  discoveryEnabled: boolean;
  lastDiscoveryTime?: string;
}

// ─── Chat DTOs ────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
}

export interface ChatSendRequest {
  sessionId: string;
  messages: ChatMessage[];
  modelId?: string;
  stream: boolean;
  maxTokens?: number;
  systemPrompt?: string;
}

export interface ChatSendResponse {
  requestId: string;
  sessionId: string;
  status: 'streaming';
  streamUrl: string;
  websocketTopic: string;
}

// ─── Voice DTOs ───────────────────────────────────────────────────────────────

export interface VoiceSummary {
  sttEnabled: boolean;
  ttsEnabled: boolean;
  sttEngine: string;
  ttsEngine: string;
  sttDeviceMode: WorkloadDevice;
  ttsDeviceMode: WorkloadDevice;
}

// ─── System DTOs ──────────────────────────────────────────────────────────────

export interface SystemInfo {
  appName: string;
  appEnv: string;
  version: string;
  apiVersion: string;
  uptime: string;
  status: 'healthy' | 'degraded' | 'initializing';
}

export interface HealthCheck {
  status: 'pass' | 'warn' | 'fail';
  message?: string;
}

export interface HealthResponse {
  status: 'pass' | 'warn' | 'fail';
  version: string;
  timestamp: string;
  checks: Record<string, HealthCheck>;
}

// ─── Feature flags ────────────────────────────────────────────────────────────

export interface FeatureFlags {
  chat: boolean;
  voice: boolean;
  vision: boolean;
  terminal: boolean;
  memory: boolean;
  tools: boolean;
  execution: boolean;
  search: boolean;
  localControl: boolean;
  selfImprovement: boolean;
  localLlm: boolean;
  gpuMonitor: boolean;
}

// ─── Bootstrap DTO ────────────────────────────────────────────────────────────

export interface BootstrapData {
  system: SystemInfo;
  providers: ProvidersSummary;
  models: ModelsSummary;
  settings: {
    theme: string;
    language: string;
    streamingEnabled: boolean;
  };
  voice: VoiceSummary;
  features: FeatureFlags;
  gpu: GPUStatus;
}
