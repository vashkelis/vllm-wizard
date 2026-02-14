"""VRAM memory calculations for vLLM sizing."""

from typing import Optional

from vllm_wizard.models.metadata import ModelMetadata
from vllm_wizard.schemas.inputs import DType, KVCacheDType, Quantization
from vllm_wizard.schemas.outputs import FeasibilityReport, OOMRisk

# Bytes per parameter for different data types
DTYPE_BYTES: dict[str, float] = {
    "fp32": 4.0,
    "fp16": 2.0,
    "bf16": 2.0,
    "int8": 1.0,
    "fp8": 1.0,
}

# Quantization bytes per parameter (includes overhead for scales/zeros)
QUANT_BYTES: dict[str, float] = {
    "none": 2.0,  # Default to fp16
    "awq": 0.55,  # 4-bit + ~10% overhead
    "gptq": 0.55,  # 4-bit + ~10% overhead
    "int8": 1.0,
    "fp8": 1.0,
}

# Bytes to GiB conversion
BYTES_TO_GIB = 1024**3


def compute_weights_memory(
    params_b: float,
    dtype: DType = DType.AUTO,
    quantization: Quantization = Quantization.NONE,
) -> int:
    """Compute model weights memory in bytes.

    Args:
        params_b: Model parameters in billions
        dtype: Weight data type
        quantization: Quantization method

    Returns:
        Memory in bytes
    """
    params = int(params_b * 1e9)

    # Determine bytes per parameter
    if quantization != Quantization.NONE:
        bytes_per_param = QUANT_BYTES.get(quantization.value, 2.0)
    else:
        # Map dtype to bytes
        dtype_str = dtype.value if dtype != DType.AUTO else "bf16"
        bytes_per_param = DTYPE_BYTES.get(dtype_str, 2.0)

    return int(params * bytes_per_param)


def compute_kv_cache_memory(
    metadata: ModelMetadata,
    context_len: int,
    concurrency: int,
    kv_dtype: KVCacheDType = KVCacheDType.AUTO,
    dtype: DType = DType.AUTO,
    fragmentation_factor: float = 1.15,
) -> int:
    """Compute KV cache memory in bytes.

    Per token per layer KV bytes:
    - K: num_kv_heads * head_dim
    - V: num_kv_heads * head_dim
    - Total elements per token per layer = 2 * num_kv_heads * head_dim

    Args:
        metadata: Model metadata
        context_len: Maximum context length (tokens)
        concurrency: Number of concurrent sequences
        kv_dtype: KV cache data type
        dtype: Model weight dtype (used if kv_dtype is auto)
        fragmentation_factor: Safety factor for fragmentation

    Returns:
        Memory in bytes
    """
    head_dim = metadata.head_dim
    num_kv_heads = metadata.num_key_value_heads
    num_layers = metadata.num_hidden_layers

    # Elements per token per layer (K + V)
    elements_per_token_per_layer = 2 * num_kv_heads * head_dim

    # Determine bytes per element
    if kv_dtype == KVCacheDType.AUTO:
        # Default to model dtype
        kv_dtype_str = dtype.value if dtype != DType.AUTO else "bf16"
    else:
        kv_dtype_str = kv_dtype.value

    # Map KV dtype to bytes
    if "fp8" in kv_dtype_str:
        bytes_per_element = 1.0
    elif kv_dtype_str in ("fp16", "bf16"):
        bytes_per_element = 2.0
    elif kv_dtype_str == "fp32":
        bytes_per_element = 4.0
    else:
        bytes_per_element = 2.0  # Default to fp16

    # Total KV cache bytes
    kv_bytes = (
        elements_per_token_per_layer
        * num_layers
        * context_len
        * concurrency
        * bytes_per_element
    )

    # Apply fragmentation factor
    kv_bytes = int(kv_bytes * fragmentation_factor)

    return kv_bytes


def compute_overhead(
    vram_total_bytes: int,
    tp_size: int = 1,
    fixed_overhead_gb: Optional[float] = None,
) -> int:
    """Compute framework overhead in bytes.

    Args:
        vram_total_bytes: Total VRAM in bytes
        tp_size: Tensor parallel size
        fixed_overhead_gb: Fixed overhead in GB (overrides calculation)

    Returns:
        Overhead in bytes
    """
    if fixed_overhead_gb is not None:
        return int(fixed_overhead_gb * BYTES_TO_GIB)

    vram_total_gb = vram_total_bytes / BYTES_TO_GIB

    # Base overhead: max(1.0GB, 2% of VRAM)
    base_overhead_gb = max(1.0, 0.02 * vram_total_gb)

    # Multi-GPU communication buffer overhead
    comm_overhead_gb = 0.25 * (tp_size - 1) if tp_size > 1 else 0.0

    total_overhead_gb = base_overhead_gb + comm_overhead_gb

    return int(total_overhead_gb * BYTES_TO_GIB)


def compute_feasibility(
    weights_bytes: int,
    kv_cache_bytes: int,
    overhead_bytes: int,
    vram_total_bytes: int,
    gpu_memory_utilization: float = 0.90,
    headroom_gb: float = 1.0,
    context_len: int = 4096,
    concurrency: int = 1,
    metadata: Optional[ModelMetadata] = None,
    kv_dtype: KVCacheDType = KVCacheDType.AUTO,
    dtype: DType = DType.AUTO,
    fragmentation_factor: float = 1.15,
) -> FeasibilityReport:
    """Compute VRAM feasibility analysis.

    Args:
        weights_bytes: Model weights memory in bytes
        kv_cache_bytes: KV cache memory in bytes
        overhead_bytes: Overhead memory in bytes
        vram_total_bytes: Total VRAM in bytes
        gpu_memory_utilization: Target GPU memory utilization
        headroom_gb: Minimum headroom in GB
        context_len: Context length for max calculations
        concurrency: Concurrency for max calculations
        metadata: Model metadata for max calculations
        kv_dtype: KV cache dtype
        dtype: Model dtype
        fragmentation_factor: Fragmentation factor

    Returns:
        FeasibilityReport with analysis results
    """
    # Calculate allocatable VRAM
    allocatable_bytes = int(vram_total_bytes * gpu_memory_utilization)

    # Total required
    required_bytes = weights_bytes + kv_cache_bytes + overhead_bytes

    # Headroom
    headroom_bytes = allocatable_bytes - required_bytes
    headroom_gb_actual = headroom_bytes / BYTES_TO_GIB

    # Feasibility check
    fits = headroom_bytes >= (headroom_gb * BYTES_TO_GIB)

    # OOM risk classification
    if headroom_gb_actual >= 2.0:
        oom_risk = OOMRisk.LOW
    elif headroom_gb_actual >= 0:
        oom_risk = OOMRisk.MEDIUM
    else:
        oom_risk = OOMRisk.HIGH

    # Calculate max concurrency and context
    max_concurrency = 0
    max_context = 0

    if metadata:
        max_concurrency = compute_max_concurrency_at_context(
            allocatable_bytes=allocatable_bytes,
            weights_bytes=weights_bytes,
            overhead_bytes=overhead_bytes,
            metadata=metadata,
            context_len=context_len,
            kv_dtype=kv_dtype,
            dtype=dtype,
            fragmentation_factor=fragmentation_factor,
        )

        max_context = compute_max_context_at_concurrency(
            allocatable_bytes=allocatable_bytes,
            weights_bytes=weights_bytes,
            overhead_bytes=overhead_bytes,
            metadata=metadata,
            concurrency=concurrency,
            kv_dtype=kv_dtype,
            dtype=dtype,
            fragmentation_factor=fragmentation_factor,
        )

    # Generate warnings
    warnings: list[str] = []

    if not fits:
        warnings.append(
            f"Configuration does not fit in VRAM. "
            f"Required: {required_bytes / BYTES_TO_GIB:.2f} GiB, "
            f"Available: {allocatable_bytes / BYTES_TO_GIB:.2f} GiB"
        )

    if oom_risk == OOMRisk.HIGH:
        warnings.append("High OOM risk - consider reducing context length or using quantization")
    elif oom_risk == OOMRisk.MEDIUM:
        warnings.append("Medium OOM risk - monitor memory usage during inference")

    kv_ratio = kv_cache_bytes / allocatable_bytes if allocatable_bytes > 0 else 0
    if kv_ratio > 0.5:
        warnings.append(
            f"KV cache uses {kv_ratio*100:.1f}% of available VRAM - "
            f"consider FP8 KV cache or shorter context"
        )

    return FeasibilityReport(
        fits=fits,
        oom_risk=oom_risk,
        vram_total_gb=vram_total_bytes / BYTES_TO_GIB,
        vram_target_alloc_gb=allocatable_bytes / BYTES_TO_GIB,
        weights_gb=weights_bytes / BYTES_TO_GIB,
        kv_cache_gb=kv_cache_bytes / BYTES_TO_GIB,
        overhead_gb=overhead_bytes / BYTES_TO_GIB,
        headroom_gb=max(0, headroom_gb_actual),
        max_concurrency_at_context=max_concurrency,
        max_context_at_concurrency=max_context,
        warnings=warnings,
    )


def compute_max_concurrency_at_context(
    allocatable_bytes: int,
    weights_bytes: int,
    overhead_bytes: int,
    metadata: ModelMetadata,
    context_len: int,
    kv_dtype: KVCacheDType = KVCacheDType.AUTO,
    dtype: DType = DType.AUTO,
    fragmentation_factor: float = 1.15,
) -> int:
    """Compute maximum concurrency at a given context length.

    Args:
        allocatable_bytes: Allocatable VRAM in bytes
        weights_bytes: Model weights in bytes
        overhead_bytes: Overhead in bytes
        metadata: Model metadata
        context_len: Target context length
        kv_dtype: KV cache dtype
        dtype: Model dtype
        fragmentation_factor: Fragmentation factor

    Returns:
        Maximum number of concurrent sequences (0 if doesn't fit)
    """
    available_for_kv = allocatable_bytes - weights_bytes - overhead_bytes

    if available_for_kv <= 0:
        return 0

    # Compute KV cache for single sequence
    kv_per_seq = compute_kv_cache_memory(
        metadata=metadata,
        context_len=context_len,
        concurrency=1,
        kv_dtype=kv_dtype,
        dtype=dtype,
        fragmentation_factor=fragmentation_factor,
    )

    if kv_per_seq <= 0:
        return 0

    return max(0, available_for_kv // kv_per_seq)


def compute_max_context_at_concurrency(
    allocatable_bytes: int,
    weights_bytes: int,
    overhead_bytes: int,
    metadata: ModelMetadata,
    concurrency: int,
    kv_dtype: KVCacheDType = KVCacheDType.AUTO,
    dtype: DType = DType.AUTO,
    fragmentation_factor: float = 1.15,
) -> int:
    """Compute maximum context length at a given concurrency.

    Args:
        allocatable_bytes: Allocatable VRAM in bytes
        weights_bytes: Model weights in bytes
        overhead_bytes: Overhead in bytes
        metadata: Model metadata
        concurrency: Target concurrency
        kv_dtype: KV cache dtype
        dtype: Model dtype
        fragmentation_factor: Fragmentation factor

    Returns:
        Maximum context length (0 if doesn't fit)
    """
    available_for_kv = allocatable_bytes - weights_bytes - overhead_bytes

    if available_for_kv <= 0 or concurrency <= 0:
        return 0

    # Compute KV cache per token per sequence
    kv_per_token_per_seq = compute_kv_cache_memory(
        metadata=metadata,
        context_len=1,
        concurrency=1,
        kv_dtype=kv_dtype,
        dtype=dtype,
        fragmentation_factor=fragmentation_factor,
    )

    if kv_per_token_per_seq <= 0:
        return 0

    # Total tokens available across all sequences
    total_tokens = available_for_kv // kv_per_token_per_seq

    # Divide by concurrency
    return max(0, total_tokens // concurrency)
