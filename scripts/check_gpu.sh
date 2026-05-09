#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "  Checking NVIDIA GPU availability..."
echo ""

# Check nvidia-smi on host
if command -v nvidia-smi &>/dev/null; then
  echo "  [host] nvidia-smi found:"
  nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap \
             --format=csv,noheader 2>/dev/null \
    | while IFS=',' read -r name mem driver cap; do
        echo "    GPU:     $name"
        echo "    VRAM:    $mem"
        echo "    Driver:  $driver"
        echo "    Compute: $cap"
      done
else
  echo "  [host] nvidia-smi not found."
fi

echo ""

# Check via Docker
echo "  [docker] Testing NVIDIA Container Toolkit..."
if docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi &>/dev/null; then
  echo "  [docker] GPU available via Docker.  Docker GPU support: OK"
else
  echo "  [docker] GPU not available via Docker or toolkit not installed."
  echo "           Install NVIDIA Container Toolkit:"
  echo "           https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
fi

echo ""

# Check Python/torch
if command -v python3 &>/dev/null; then
  echo "  [python] Checking torch/CUDA..."
  python3 -c "
try:
    import torch
    avail = torch.cuda.is_available()
    count = torch.cuda.device_count() if avail else 0
    print(f'  [python] torch: {torch.__version__}  CUDA: {avail}  devices: {count}')
    if avail:
        for i in range(count):
            print(f'           GPU {i}: {torch.cuda.get_device_name(i)}')
except ImportError:
    print('  [python] torch not installed (optional)')
" 2>/dev/null || echo "  [python] torch check failed"
fi

echo ""
