"""Performance estimation heuristics for vLLM sizing."""

from typing import Optional

from vllm_wizard.schemas.inputs import Interconnect, Quantization
from vllm_wizard.schemas.outputs import PerfEstimate

# Baseline decode tokens per second by GPU class
# These are rough estimates for ~7B parameter models at moderate context
GPU_BASELINE_DECODE_TPS: dict[str, float] = {
    # High-end consumer
    "4090": 150.0,
    "3090 ti": 120.0,
    "3090": 110.0,
    "4080": 130.0,
    "3080 ti": 90.0,
    "3080": 80.0,
    # Professional
    "rtx a6000": 130.0,
    "rtx a5000": 100.0,
    "rtx a4000": 70.0,
    # Datacenter
    "h200": 400.0,
    "h100": 350.0,
    "l40s": 180.0,
    "l40": 160.0,
    "a100 80gb": 220.0,
    "a100 40gb": 200.0,
    "a100": 200.0,
    "l4": 100.0,
    "a10g": 90.0,
    "a10": 90.0,
    "v100 32gb": 80.0,
    "v100": 70.0,
    "t4": 50.0,
}

# Baseline prefill tokens per second by GPU class
GPU_BASELINE_PREFILL_TPS: dict[str, float] = {
    "4090": 3000.0,
    "3090": 2200.0,
    "h200": 12000.0,
    "h100": 10000.0,
    "a100 80gb": 5000.0,
    "a100": 4500.0,
    "l40s": 4000.0,
    "l4": 2000.0,
    "t4": 1000.0,
}

# Default baseline for unknown GPUs
DEFAULT_DECODE_TPS = 80.0
DEFAULT_PREFILL_TPS = 2000.0


def _get_gpu_baseline(
    gpu_name: str, baseline_table: dict[str, float], default: float
) -> float:
    """Get baseline TPS for a GPU from lookup table."""
    name_lower = gpu_name.lower()

    # Exact match
    for key, value in baseline_table.items():
        if key in name_lower:
            return value

    return default


def _scale_by_model_size(base_tps: float, params_b: float, reference_params_b: float = 7.0) -> float:
    """Scale TPS by model size relative to reference.

    Uses inverse scaling with exponent ~0.85 (between linear and sqrt).
    """
    if params_b <= 0:
        return base_tps

    # Scale factor: (reference / actual)^0.85
    scale = (reference_params_b / params_b) ** 0.85
    return base_tps * scale


def _scale_by_tensor_parallel(
    tps: float,
    tp_size: int,
    interconnect: Interconnect = Interconnect.UNKNOWN,
) -> float:
    """Scale TPS by tensor parallel size.

    TP generally improves throughput but with communication overhead.
    """
    if tp_size <= 1:
        return tps

    # Efficiency factor based on interconnect
    if interconnect == Interconnect.NVLINK:
        efficiency = 0.90  # Good scaling with NVLink
    elif interconnect == Interconnect.PCIE:
        efficiency = 0.75  # PCIe has more overhead
    else:
        efficiency = 0.80  # Unknown, assume moderate

    # Linear scaling with efficiency penalty
    return tps * tp_size * efficiency


def _scale_by_context(tps: float, context_len: int, reference_context: int = 2048) -> float:
    """Scale TPS by context length.

    Longer contexts reduce decode TPS due to attention overhead.
    """
    if context_len <= reference_context:
        return tps

    # Mild degradation: sqrt scaling
    scale = (reference_context / context_len) ** 0.3
    return tps * scale


def _scale_by_quantization(tps: float, quantization: Quantization) -> float:
    """Scale TPS by quantization.

    Quantization can provide modest speedups.
    """
    speedup_factors = {
        Quantization.NONE: 1.0,
        Quantization.AWQ: 1.1,
        Quantization.GPTQ: 1.05,
        Quantization.INT8: 1.15,
        Quantization.FP8: 1.2,
    }

    return tps * speedup_factors.get(quantization, 1.0)


def estimate_performance(
    gpu_name: str,
    params_b: float,
    tp_size: int = 1,
    context_len: int = 4096,
    prompt_tokens: int = 512,
    quantization: Quantization = Quantization.NONE,
    interconnect: Interconnect = Interconnect.UNKNOWN,
    num_gpus: int = 1,
) -> PerfEstimate:
    """Estimate approximate performance metrics.

    Returns ranges to emphasize the heuristic nature of estimates.

    Args:
        gpu_name: GPU model name
        params_b: Model parameters in billions
        tp_size: Tensor parallel size
        context_len: Maximum context length
        prompt_tokens: Typical prompt token count
        quantization: Quantization method
        interconnect: GPU interconnect type
        num_gpus: Number of GPUs

    Returns:
        PerfEstimate with ranges and assumptions
    """
    # Get baseline decode TPS
    base_decode = _get_gpu_baseline(gpu_name, GPU_BASELINE_DECODE_TPS, DEFAULT_DECODE_TPS)
    base_prefill = _get_gpu_baseline(gpu_name, GPU_BASELINE_PREFILL_TPS, DEFAULT_PREFILL_TPS)

    # Scale by model size
    decode_tps = _scale_by_model_size(base_decode, params_b)
    prefill_tps = _scale_by_model_size(base_prefill, params_b, reference_params_b=7.0)

    # Scale by tensor parallel
    decode_tps = _scale_by_tensor_parallel(decode_tps, tp_size, interconnect)
    prefill_tps = _scale_by_tensor_parallel(prefill_tps, tp_size, interconnect)

    # Scale by context length
    decode_tps = _scale_by_context(decode_tps, context_len)

    # Scale by quantization
    decode_tps = _scale_by_quantization(decode_tps, quantization)
    prefill_tps = _scale_by_quantization(prefill_tps, quantization)

    # Generate ranges (±30% for decode, ±40% for prefill)
    decode_low = decode_tps * 0.7
    decode_high = decode_tps * 1.3

    prefill_low = prefill_tps * 0.6
    prefill_high = prefill_tps * 1.4

    # Estimate TTFT (Time To First Token)
    # TTFT ≈ prompt_tokens / prefill_tps * 1000 (ms)
    ttft_estimate = (prompt_tokens / prefill_tps) * 1000
    ttft_low = (prompt_tokens / prefill_high) * 1000
    ttft_high = (prompt_tokens / prefill_low) * 1000

    # Build assumptions list
    assumptions = [
        "Heuristic estimate; real performance depends on vLLM version, CUDA driver, and kernel selection.",
        f"Based on reference {gpu_name} performance scaled for {params_b:.1f}B parameters.",
        f"Context length scaling assumes typical attention patterns at {context_len} tokens.",
    ]

    if tp_size > 1:
        assumptions.append(
            f"Tensor parallel {tp_size}x scaling assumes {interconnect.value} interconnect efficiency."
        )

    if quantization != Quantization.NONE:
        assumptions.append(f"Quantization ({quantization.value}) speedup factor applied.")

    assumptions.append(
        "Actual throughput varies significantly with batch size, prompt/generation ratio, and memory pressure."
    )

    return PerfEstimate(
        decode_toks_per_s_range=(round(decode_low, 1), round(decode_high, 1)),
        prefill_toks_per_s_range=(round(prefill_low, 1), round(prefill_high, 1)),
        ttft_ms_range=(round(ttft_low, 1), round(ttft_high, 1)),
        assumptions=assumptions,
    )
