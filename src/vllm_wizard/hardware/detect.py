"""GPU detection via nvidia-smi."""

import re
import subprocess
from typing import Optional

from vllm_wizard.schemas.outputs import GPUInfo


def detect_gpus() -> list[GPUInfo]:
    """Detect available NVIDIA GPUs using nvidia-smi.

    Returns:
        List of GPUInfo objects with detected GPU information.
        Returns empty list if nvidia-smi fails or no GPUs found.
    """
    try:
        # Query GPU name and memory
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        gpus: list[GPUInfo] = []

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                name = parts[0]
                try:
                    vram_mib = int(float(parts[1]))
                except ValueError:
                    continue

                gpus.append(GPUInfo(name=name, vram_mib=vram_mib))

        # Try to get driver and CUDA version
        driver_version, cuda_version = _get_nvidia_versions()

        # Update all GPUs with version info
        for gpu in gpus:
            gpu.driver_version = driver_version
            gpu.cuda_version = cuda_version

        # Try to get compute capability for each GPU
        compute_caps = _get_compute_capabilities()
        for i, gpu in enumerate(gpus):
            if i < len(compute_caps):
                gpu.compute_capability = compute_caps[i]

        return gpus

    except FileNotFoundError:
        # nvidia-smi not found
        return []
    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return []


def _get_nvidia_versions() -> tuple[Optional[str], Optional[str]]:
    """Get NVIDIA driver and CUDA versions."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        driver_version = None
        if result.returncode == 0 and result.stdout.strip():
            driver_version = result.stdout.strip().split("\n")[0]

        # Get CUDA version from nvidia-smi header
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        cuda_version = None
        if result.returncode == 0:
            # Parse CUDA Version from nvidia-smi output
            match = re.search(r"CUDA Version:\s*([\d.]+)", result.stdout)
            if match:
                cuda_version = match.group(1)

        return driver_version, cuda_version

    except Exception:
        return None, None


def _get_compute_capabilities() -> list[str]:
    """Get compute capabilities for each GPU."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=compute_cap",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return []

        caps = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                caps.append(line)

        return caps

    except Exception:
        return []


def recommend_tensor_parallel(gpus: list[GPUInfo]) -> int:
    """Recommend tensor parallel size based on available GPUs.

    Chooses the largest power of 2 that is <= number of GPUs.

    Args:
        gpus: List of detected GPUs

    Returns:
        Recommended tensor parallel size (minimum 1)
    """
    num_gpus = len(gpus)

    if num_gpus <= 1:
        return 1

    # Find largest power of 2 <= num_gpus
    tp_size = 1
    while tp_size * 2 <= num_gpus:
        tp_size *= 2

    return tp_size


def get_gpu_by_name(name: str) -> Optional[GPUInfo]:
    """Create a GPUInfo from a known GPU name.

    Provides approximate VRAM for common GPUs when auto-detection fails.

    Args:
        name: GPU name (e.g., "RTX 4090", "A100 80GB")

    Returns:
        GPUInfo with approximate specs, or None if unknown
    """
    # Known GPU VRAM in MiB
    known_gpus: dict[str, int] = {
        # Consumer NVIDIA
        "rtx 4090": 24576,
        "rtx 4080": 16384,
        "rtx 4070 ti": 12288,
        "rtx 4070": 12288,
        "rtx 3090 ti": 24576,
        "rtx 3090": 24576,
        "rtx 3080 ti": 12288,
        "rtx 3080": 10240,
        "rtx 3070 ti": 8192,
        "rtx 3070": 8192,
        "rtx 3060 ti": 8192,
        "rtx 3060": 12288,
        "rtx a6000": 49152,
        "rtx a5000": 24576,
        "rtx a4000": 16384,
        # Datacenter NVIDIA
        "a100 80gb": 81920,
        "a100 40gb": 40960,
        "a100": 40960,
        "h100 80gb": 81920,
        "h100": 81920,
        "h200": 143360,
        "l40s": 49152,
        "l40": 49152,
        "l4": 24576,
        "a10g": 24576,
        "a10": 24576,
        "v100 32gb": 32768,
        "v100 16gb": 16384,
        "v100": 16384,
        "t4": 16384,
        "p100 16gb": 16384,
        "p100": 16384,
        # Apple Silicon (for reference)
        "m1 max": 32768,
        "m1 ultra": 65536,
        "m2 max": 32768,
        "m2 ultra": 65536,
        "m3 max": 40960,
    }

    name_lower = name.lower().strip()

    # Exact match first
    if name_lower in known_gpus:
        return GPUInfo(name=name, vram_mib=known_gpus[name_lower])

    # Partial match
    for known_name, vram in known_gpus.items():
        if known_name in name_lower or name_lower in known_name:
            return GPUInfo(name=name, vram_mib=vram)

    return None
