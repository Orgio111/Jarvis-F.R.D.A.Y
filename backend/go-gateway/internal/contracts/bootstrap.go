package contracts

// BootstrapData is the full system state returned by GET /api/bootstrap.
// The frontend MUST call this endpoint first before using any other feature.
type BootstrapData struct {
	System   SystemInfo      `json:"system"`
	Providers ProvidersSummary `json:"providers"`
	Models   ModelsSummary   `json:"models"`
	Settings SettingsSummary `json:"settings"`
	Voice    VoiceSummary    `json:"voice"`
	Features FeatureFlags    `json:"features"`
	GPU      GPUStatus       `json:"gpu"`
}

type SystemInfo struct {
	AppName    string `json:"appName"`
	AppEnv     string `json:"appEnv"`
	Version    string `json:"version"`
	APIVersion string `json:"apiVersion"`
	Uptime     string `json:"uptime"`
	Status     string `json:"status"` // "healthy" | "degraded" | "initializing"
}

type ProvidersSummary struct {
	Primary   ProviderStatus   `json:"primary"`
	Fallback  ProviderStatus   `json:"fallback"`
	Available []ProviderStatus `json:"available"`
}

type ProviderStatus struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Status      string `json:"status"` // "available" | "provider_unavailable" | "error"
	Reason      string `json:"reason,omitempty"`
	ModelCount  int    `json:"modelCount"`
	DeviceMode  string `json:"deviceMode"` // "cloud" | "gpu" | "cpu" | "disabled"
}

type ModelsSummary struct {
	DefaultChatModel   string `json:"defaultChatModel"`
	DefaultCoderModel  string `json:"defaultCoderModel"`
	DefaultFastModel   string `json:"defaultFastModel"`
	TotalAvailable     int    `json:"totalAvailable"`
	DiscoveryEnabled   bool   `json:"discoveryEnabled"`
	LastDiscoveryTime  string `json:"lastDiscoveryTime,omitempty"`
}

type SettingsSummary struct {
	Theme           string `json:"theme"`
	Language        string `json:"language"`
	StreamingEnabled bool  `json:"streamingEnabled"`
}

type VoiceSummary struct {
	STTEnabled    bool   `json:"sttEnabled"`
	TTSEnabled    bool   `json:"ttsEnabled"`
	STTEngine     string `json:"sttEngine"`
	TTSEngine     string `json:"ttsEngine"`
	STTDeviceMode string `json:"sttDeviceMode"`
	TTSDeviceMode string `json:"ttsDeviceMode"`
}

type FeatureFlags struct {
	Chat           bool `json:"chat"`
	Voice          bool `json:"voice"`
	Vision         bool `json:"vision"`
	Terminal       bool `json:"terminal"`
	Memory         bool `json:"memory"`
	Tools          bool `json:"tools"`
	Execution      bool `json:"execution"`
	Search         bool `json:"search"`
	LocalControl   bool `json:"localControl"`
	SelfImprovement bool `json:"selfImprovement"`
	LocalLLM       bool `json:"localLlm"`
	GPUMonitor     bool `json:"gpuMonitor"`
}

// DefaultBootstrapData returns a safe default when the Python AI service is
// unavailable. The frontend shows this as a degraded-mode bootstrap.
func DefaultBootstrapData(appName, appEnv, version string, gpuRequired bool) BootstrapData {
	unavailableReason := "provider_unavailable: API key not configured"
	return BootstrapData{
		System: SystemInfo{
			AppName:    appName,
			AppEnv:     appEnv,
			Version:    version,
			APIVersion: "v1",
			Status:     "degraded",
		},
		Providers: ProvidersSummary{
			Primary: ProviderStatus{
				ID:     "nvidia_nim",
				Name:   "NVIDIA NIM",
				Status: "provider_unavailable",
				Reason: unavailableReason,
			},
			Fallback: ProviderStatus{
				ID:     "openrouter",
				Name:   "OpenRouter",
				Status: "provider_unavailable",
				Reason: unavailableReason,
			},
			Available: []ProviderStatus{},
		},
		Models: ModelsSummary{
			TotalAvailable:   0,
			DiscoveryEnabled: true,
		},
		Settings: SettingsSummary{
			Theme:            "dark",
			Language:         "en",
			StreamingEnabled: true,
		},
		Voice: VoiceSummary{
			STTEnabled: false,
			TTSEnabled: false,
		},
		Features: FeatureFlags{
			Chat:      true,
			Voice:     false,
			Vision:    false,
			Terminal:  true,
			Memory:    false,
			Tools:     true,
			Execution: false,
			Search:    false,
			LocalControl: true,
			SelfImprovement: false,
			LocalLLM:   false,
			GPUMonitor: true,
		},
		GPU: CPUFallbackGPUStatus(gpuRequired),
	}
}
