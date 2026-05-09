package contracts

// GPUStatus is the canonical GPU status DTO returned by GET /api/gpu/status
type GPUStatus struct {
	Enabled       bool            `json:"enabled"`
	Available     bool            `json:"available"`
	Required      bool            `json:"required"`
	Provider      string          `json:"provider"`
	DeviceCount   int             `json:"deviceCount"`
	ActiveDevice  string          `json:"activeDevice"`
	CUDAAvailable bool            `json:"cudaAvailable"`
	CUDAVersion   *string         `json:"cudaVersion"`
	DriverVersion *string         `json:"driverVersion"`
	VRAM          GPUMemory       `json:"vram"`
	Utilization   GPUUtilization  `json:"utilization"`
	Workloads     GPUWorkloads    `json:"workloads"`
	Fallback      GPUFallback     `json:"fallback"`
}

type GPUMemory struct {
	TotalMB int64 `json:"totalMb"`
	UsedMB  int64 `json:"usedMb"`
	FreeMB  int64 `json:"freeMb"`
}

type GPUUtilization struct {
	GPUPercent    float64 `json:"gpuPercent"`
	MemoryPercent float64 `json:"memoryPercent"`
	TemperatureC  float64 `json:"temperatureC"`
	PowerWatts    float64 `json:"powerWatts"`
}

// WorkloadDevice enumerates device assignment values
type WorkloadDevice = string

const (
	WorkloadGPU      WorkloadDevice = "gpu"
	WorkloadCPU      WorkloadDevice = "cpu"
	WorkloadCloud    WorkloadDevice = "cloud"
	WorkloadDisabled WorkloadDevice = "disabled"
)

type GPUWorkloads struct {
	LocalLLM        WorkloadDevice `json:"localLlm"`
	STT             WorkloadDevice `json:"stt"`
	TTS             WorkloadDevice `json:"tts"`
	Embeddings      WorkloadDevice `json:"embeddings"`
	FAISS           WorkloadDevice `json:"faiss"`
	Vision          WorkloadDevice `json:"vision"`
	RAG             WorkloadDevice `json:"rag"`
	MemorySynthesis WorkloadDevice `json:"memorySynthesis"`
}

type GPUFallback struct {
	CPUFallbackAllowed bool    `json:"cpuFallbackAllowed"`
	CPUFallbackActive  bool    `json:"cpuFallbackActive"`
	Reason             *string `json:"reason"`
}

// GPUMetrics holds time-series GPU utilization data
type GPUMetrics struct {
	Timestamp     string         `json:"timestamp"`
	DeviceIndex   int            `json:"deviceIndex"`
	DeviceName    string         `json:"deviceName"`
	Utilization   GPUUtilization `json:"utilization"`
	VRAM          GPUMemory      `json:"vram"`
}

// GPUSettings holds mutable GPU configuration
type GPUSettings struct {
	Enabled            bool   `json:"enabled"`
	Required           bool   `json:"required"`
	AllowCPUFallback   bool   `json:"allowCpuFallback"`
	PreferHalfPrecision bool  `json:"preferHalfPrecision"`
	EnableMixedPrecision bool `json:"enableMixedPrecision"`
	MemorySoftLimitMB  int64  `json:"memorySoftLimitMb"`
	MemoryHardLimitMB  int64  `json:"memoryHardLimitMb"`
}

// CPUFallbackGPUStatus returns a valid GPU status representing CPU-only mode.
// Used when Python AI service is unavailable or GPU is not configured.
func CPUFallbackGPUStatus(gpuRequired bool) GPUStatus {
	reason := "GPU not configured or Python AI service unavailable"
	cpuDevice := "cpu"
	_ = cpuDevice
	return GPUStatus{
		Enabled:       false,
		Available:     false,
		Required:      gpuRequired,
		Provider:      "none",
		DeviceCount:   0,
		ActiveDevice:  "cpu",
		CUDAAvailable: false,
		CUDAVersion:   nil,
		DriverVersion: nil,
		VRAM:          GPUMemory{},
		Utilization:   GPUUtilization{},
		Workloads: GPUWorkloads{
			LocalLLM:        WorkloadCPU,
			STT:             WorkloadCPU,
			TTS:             WorkloadCPU,
			Embeddings:      WorkloadCPU,
			FAISS:           WorkloadCPU,
			Vision:          WorkloadCPU,
			RAG:             WorkloadCPU,
			MemorySynthesis: WorkloadCPU,
		},
		Fallback: GPUFallback{
			CPUFallbackAllowed: true,
			CPUFallbackActive:  true,
			Reason:             &reason,
		},
	}
}
