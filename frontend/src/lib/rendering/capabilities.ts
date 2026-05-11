/**
 * GPU rendering capability detection.
 * All probes are safe — they never throw and degrade gracefully.
 */

export interface RenderingCapabilities {
  webgl: boolean;
  webgl2: boolean;
  webgpu: boolean;
  hardwareConcurrency: number;
  deviceMemoryGB: number | null;
  maxTextureSize: number;
  renderer: string;
  vendor: string;
  preferredColorScheme: 'dark' | 'light';
}

let _cached: RenderingCapabilities | null = null;

export async function detectCapabilities(): Promise<RenderingCapabilities> {
  if (_cached) return _cached;

  let webgl = false;
  let webgl2 = false;
  let maxTextureSize = 0;
  let renderer = 'unknown';
  let vendor = 'unknown';

  // WebGL2 probe
  try {
    const canvas = document.createElement('canvas');
    const gl2 = canvas.getContext('webgl2');
    if (gl2) {
      webgl2 = true;
      webgl = true;
      maxTextureSize = gl2.getParameter(gl2.MAX_TEXTURE_SIZE) as number;
      const ext = gl2.getExtension('WEBGL_debug_renderer_info');
      if (ext) {
        renderer = gl2.getParameter(ext.UNMASKED_RENDERER_WEBGL) as string;
        vendor = gl2.getParameter(ext.UNMASKED_VENDOR_WEBGL) as string;
      }
    } else {
      // WebGL1 probe
      const gl1 = canvas.getContext('webgl');
      if (gl1) {
        webgl = true;
        maxTextureSize = gl1.getParameter(gl1.MAX_TEXTURE_SIZE) as number;
      }
    }
  } catch {
    // Canvas / context unavailable
  }

  // WebGPU probe
  let webgpu = false;
  try {
    if ('gpu' in navigator && (navigator as Navigator & { gpu?: { requestAdapter: () => Promise<unknown> } }).gpu) {
      const gpu = (navigator as Navigator & { gpu: { requestAdapter: () => Promise<unknown> } }).gpu;
      const adapter = await gpu.requestAdapter();
      webgpu = adapter !== null;
    }
  } catch {
    // WebGPU not available
  }

  // Device memory (non-standard but widely supported in Chrome)
  const deviceMemoryGB: number | null =
    'deviceMemory' in navigator
      ? (navigator as Navigator & { deviceMemory: number }).deviceMemory ?? null
      : null;

  const preferredColorScheme: 'dark' | 'light' =
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

  _cached = {
    webgl,
    webgl2,
    webgpu,
    hardwareConcurrency: navigator.hardwareConcurrency ?? 4,
    deviceMemoryGB,
    maxTextureSize,
    renderer,
    vendor,
    preferredColorScheme,
  };

  return _cached;
}

export function resetCapabilities(): void {
  _cached = null;
}
