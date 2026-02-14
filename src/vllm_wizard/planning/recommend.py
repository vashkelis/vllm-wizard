"""Recommendation engine for vLLM configuration."""

from typing import Optional

from vllm_wizard.models.metadata import ModelMetadata
from vllm_wizard.planning.memory import (
    BYTES_TO_GIB,
    compute_kv_cache_memory,
    compute_overhead,
    compute_weights_memory,
)
from vllm_wizard.schemas.inputs import (
    BatchingMode,
    DType,
    HardwareInput,
    KVCacheDType,
    ModelInput,
    PlanRequest,
    PolicyInput,
    Quantization,
    WorkloadInput,
)
from vllm_wizard.schemas.outputs import GPUInfo, VLLMConfig


def _is_consumer_gpu(gpu_name: str) -> bool:
    """Check if GPU is a consumer model (RTX/GeForce)."""
    name_lower = gpu_name.lower()
    return "rtx" in name_lower or "geforce" in name_lower or "titan" in name_lower


def _recommend_gpu_memory_utilization(
    gpu_name: str,
    base_utilization: float = 0.90,
) -> tuple[float, str]:
    """Recommend GPU memory utilization based on GPU type."""
    if _is_consumer_gpu(gpu_name):
        return 0.88, "Lowered to 0.88 for consumer GPU stability"
    return base_utilization, "Standard utilization for datacenter GPU"


def _recommend_tensor_parallel(
    num_gpus: int,
    weights_bytes: int,
    vram_per_gpu_bytes: int,
    requested_tp: Optional[int] = None,
) -> tuple[int, str]:
    """Recommend tensor parallel size."""
    if requested_tp is not None:
        return requested_tp, "User-specified tensor parallel size"

    if num_gpus == 1:
        return 1, "Single GPU - no tensor parallelism"

    # Find largest power of 2 <= num_gpus
    tp_size = 1
    while tp_size * 2 <= num_gpus:
        tp_size *= 2

    # Check if weights fit with this TP
    weights_per_gpu = weights_bytes / tp_size
    if weights_per_gpu > vram_per_gpu_bytes * 0.7:
        # Need more parallelism
        tp_size = min(num_gpus, tp_size * 2)
        return tp_size, f"Increased to {tp_size} to fit model weights across GPUs"

    return tp_size, f"Optimal power-of-2 tensor parallel for {num_gpus} GPUs"


def _recommend_max_model_len(
    requested: Optional[int],
    model_max: int,
    available_context: int,
) -> tuple[int, str]:
    """Recommend max model length."""
    if requested is not None:
        if requested > model_max:
            return model_max, f"Clamped to model maximum ({model_max})"
        if requested > available_context:
            return available_context, f"Reduced to fit available VRAM ({available_context})"
        return requested, "User-specified context length"

    # Use smaller of model max and what fits
    recommended = min(model_max, available_context)
    return recommended, f"Maximum context that fits in VRAM (model supports up to {model_max})"


def _recommend_quantization(
    requested: Quantization,
    fits_without_quant: bool,
) -> tuple[Optional[str], str]:
    """Recommend quantization."""
    if requested != Quantization.NONE:
        return requested.value, f"User-specified {requested.value} quantization"

    if not fits_without_quant:
        return "awq", "Recommended AWQ 4-bit quantization to fit in VRAM"

    return None, "No quantization needed - model fits in VRAM"


def _recommend_kv_cache_dtype(
    requested: KVCacheDType,
    kv_cache_pressure: float,
    gpu_name: str,
) -> tuple[Optional[str], str]:
    """Recommend KV cache dtype."""
    if requested != KVCacheDType.AUTO:
        return requested.value, f"User-specified {requested.value} KV cache dtype"

    # Suggest FP8 for high KV cache pressure on modern GPUs
    if kv_cache_pressure > 0.4:
        # Check if GPU likely supports FP8 (Hopper/Ada+)
        name_lower = gpu_name.lower()
        supports_fp8 = any(
            x in name_lower for x in ["h100", "h200", "l40", "4090", "4080", "4070"]
        )
        if supports_fp8:
            return "fp8_e4m3fn", "FP8 KV cache recommended for high context pressure (experimental)"

    return None, "Default KV cache dtype (auto)"


def _recommend_max_num_seqs(
    concurrency: int,
    mode: BatchingMode,
) -> tuple[int, str]:
    """Recommend max_num_seqs."""
    if mode == BatchingMode.THROUGHPUT:
        seqs = max(concurrency, concurrency + 4)
        return seqs, "Increased for throughput mode batching"
    elif mode == BatchingMode.LATENCY:
        return concurrency, "Matched to target concurrency for latency mode"
    else:
        seqs = concurrency + 2
        return seqs, "Slight buffer above target concurrency for balanced mode"


def _recommend_max_batched_tokens(
    prompt_tokens: int,
    gen_tokens: int,
    concurrency: int,
    mode: BatchingMode,
    vram_gb: float,
) -> tuple[int, str]:
    """Recommend max_num_batched_tokens."""
    base = (prompt_tokens + gen_tokens) * concurrency

    # Adjust based on mode
    if mode == BatchingMode.THROUGHPUT:
        multiplier = 1.5
    elif mode == BatchingMode.LATENCY:
        multiplier = 1.0
    else:
        multiplier = 1.25

    recommended = int(base * multiplier)

    # Cap based on VRAM (rough heuristic)
    max_cap = 65536 if vram_gb >= 40 else (32768 if vram_gb >= 20 else 16384)
    recommended = min(recommended, max_cap)
    recommended = max(recommended, 8192)  # Minimum

    return recommended, f"Based on workload ({prompt_tokens}+{gen_tokens}) x {concurrency} with {mode.value} mode"


def generate_recommendations(
    request: PlanRequest,
    metadata: ModelMetadata,
    gpus: list[GPUInfo],
    vram_total_bytes: int,
) -> VLLMConfig:
    """Generate recommended vLLM configuration.

    Args:
        request: Planning request with all inputs
        metadata: Model metadata
        gpus: List of available GPUs
        vram_total_bytes: Total VRAM in bytes (sum across all GPUs for TP)

    Returns:
        VLLMConfig with recommended settings
    """
    model_input: ModelInput = request.model
    hardware: HardwareInput = request.hardware
    workload: WorkloadInput = request.workload
    policy: PolicyInput = request.policy

    explanations: dict[str, str] = {}

    # Get GPU info
    gpu_name = gpus[0].name if gpus else hardware.gpu
    vram_per_gpu = vram_total_bytes // max(1, len(gpus)) if gpus else vram_total_bytes
    num_gpus = len(gpus) if gpus else hardware.gpus

    # Determine params
    params_b = model_input.params_b or (metadata.num_params / 1e9 if metadata.num_params else 7.0)

    # Initial weights calculation (to determine if we need quant)
    weights_bytes = compute_weights_memory(
        params_b=params_b,
        dtype=model_input.dtype,
        quantization=model_input.quantization,
    )

    # Tensor parallel
    tp_size, tp_explanation = _recommend_tensor_parallel(
        num_gpus=num_gpus,
        weights_bytes=weights_bytes,
        vram_per_gpu_bytes=vram_per_gpu,
        requested_tp=hardware.tensor_parallel_size,
    )
    explanations["tensor_parallel_size"] = tp_explanation

    # GPU memory utilization
    base_util = policy.gpu_memory_utilization
    gpu_util, util_explanation = _recommend_gpu_memory_utilization(gpu_name, base_util)
    explanations["gpu_memory_utilization"] = util_explanation

    # Calculate effective VRAM per TP group
    effective_vram = vram_per_gpu * tp_size
    allocatable = int(effective_vram * gpu_util)

    # Overhead
    overhead_bytes = compute_overhead(effective_vram, tp_size, policy.overhead_gb)

    # Check if fits without quantization
    weights_per_tp = weights_bytes // tp_size
    available_for_kv = allocatable - weights_per_tp - overhead_bytes

    # Initial context estimate
    context_for_check = model_input.max_model_len or metadata.max_position_embeddings
    kv_bytes_check = compute_kv_cache_memory(
        metadata=metadata,
        context_len=context_for_check,
        concurrency=workload.concurrency,
        kv_dtype=model_input.kv_cache_dtype,
        dtype=model_input.dtype,
        fragmentation_factor=policy.fragmentation_factor,
    )

    fits_without_quant = available_for_kv >= kv_bytes_check

    # Quantization
    quant_value, quant_explanation = _recommend_quantization(
        model_input.quantization, fits_without_quant
    )
    explanations["quantization"] = quant_explanation

    # Recalculate weights if quantization recommended
    effective_quant = (
        Quantization(quant_value) if quant_value else model_input.quantization
    )
    if effective_quant != model_input.quantization:
        weights_bytes = compute_weights_memory(
            params_b=params_b,
            dtype=model_input.dtype,
            quantization=effective_quant,
        )
        weights_per_tp = weights_bytes // tp_size
        available_for_kv = allocatable - weights_per_tp - overhead_bytes

    # Calculate max context that fits
    kv_per_token_per_seq = compute_kv_cache_memory(
        metadata=metadata,
        context_len=1,
        concurrency=1,
        kv_dtype=model_input.kv_cache_dtype,
        dtype=model_input.dtype,
        fragmentation_factor=policy.fragmentation_factor,
    )

    if kv_per_token_per_seq > 0 and workload.concurrency > 0:
        available_context = available_for_kv // (kv_per_token_per_seq * workload.concurrency)
    else:
        available_context = metadata.max_position_embeddings

    # Max model len
    max_model_len, len_explanation = _recommend_max_model_len(
        model_input.max_model_len,
        metadata.max_position_embeddings,
        available_context,
    )
    explanations["max_model_len"] = len_explanation

    # KV cache dtype
    kv_pressure = kv_bytes_check / allocatable if allocatable > 0 else 0
    kv_dtype_value, kv_explanation = _recommend_kv_cache_dtype(
        model_input.kv_cache_dtype, kv_pressure, gpu_name
    )
    explanations["kv_cache_dtype"] = kv_explanation

    # Max num seqs
    max_num_seqs, seqs_explanation = _recommend_max_num_seqs(
        workload.concurrency, workload.batching_mode
    )
    explanations["max_num_seqs"] = seqs_explanation

    # Max batched tokens
    max_batched_tokens, batch_explanation = _recommend_max_batched_tokens(
        workload.prompt_tokens,
        workload.gen_tokens,
        workload.concurrency,
        workload.batching_mode,
        effective_vram / BYTES_TO_GIB,
    )
    explanations["max_num_batched_tokens"] = batch_explanation

    # Dtype
    dtype_value = model_input.dtype.value
    if model_input.dtype == DType.AUTO:
        dtype_value = "auto"
        explanations["dtype"] = "Auto-detect based on model and GPU capabilities"
    else:
        explanations["dtype"] = f"User-specified {dtype_value}"

    # Build config
    config = VLLMConfig(
        model=model_input.model,
        tensor_parallel_size=tp_size,
        dtype=dtype_value,
        gpu_memory_utilization=gpu_util,
        max_model_len=max_model_len,
        kv_cache_dtype=kv_dtype_value,
        quantization=quant_value,
        max_num_seqs=max_num_seqs,
        max_num_batched_tokens=max_batched_tokens,
        trust_remote_code=model_input.trust_remote_code if model_input.trust_remote_code else None,
        explanations=explanations if request.explain else {},
    )

    return config
