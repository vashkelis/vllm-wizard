"""Output schemas for vLLM Wizard."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class OOMRisk(str, Enum):
    """Out-of-memory risk level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GPUInfo(BaseModel):
    """GPU information from detection."""

    name: str = Field(..., description="GPU name")
    vram_mib: int = Field(..., description="Total VRAM in MiB")
    compute_capability: Optional[str] = Field(None, description="CUDA compute capability")
    driver_version: Optional[str] = Field(None, description="NVIDIA driver version")
    cuda_version: Optional[str] = Field(None, description="CUDA version")

    @property
    def vram_gb(self) -> float:
        """VRAM in GB (base 1000)."""
        return self.vram_mib / 1000

    @property
    def vram_gib(self) -> float:
        """VRAM in GiB (base 1024)."""
        return self.vram_mib / 1024


class FeasibilityReport(BaseModel):
    """VRAM feasibility analysis report."""

    fits: bool = Field(..., description="Whether configuration fits in VRAM")
    oom_risk: OOMRisk = Field(..., description="OOM risk level")
    vram_total_gb: float = Field(..., description="Total VRAM in GiB")
    vram_target_alloc_gb: float = Field(..., description="Target allocation in GiB")
    weights_gb: float = Field(..., description="Model weights memory in GiB")
    kv_cache_gb: float = Field(..., description="KV cache memory in GiB")
    overhead_gb: float = Field(..., description="Overhead memory in GiB")
    headroom_gb: float = Field(..., description="Available headroom in GiB")
    max_concurrency_at_context: int = Field(
        ..., description="Max concurrency at target context length"
    )
    max_context_at_concurrency: int = Field(
        ..., description="Max context length at target concurrency"
    )
    warnings: list[str] = Field(default_factory=list, description="Warning messages")


class VLLMConfig(BaseModel):
    """Recommended vLLM serve configuration."""

    model: str = Field(..., description="Model path or HF id")
    tensor_parallel_size: int = Field(1, description="Tensor parallel size")
    dtype: str = Field("auto", description="Weight dtype")
    gpu_memory_utilization: float = Field(0.90, description="GPU memory utilization")
    max_model_len: int = Field(..., description="Maximum model length")
    kv_cache_dtype: Optional[str] = Field(None, description="KV cache dtype")
    quantization: Optional[str] = Field(None, description="Quantization method")
    swap_space: Optional[int] = Field(None, description="Swap space in GB")
    enforce_eager: Optional[bool] = Field(None, description="Enforce eager mode")
    max_num_seqs: Optional[int] = Field(None, description="Max concurrent sequences")
    max_num_batched_tokens: Optional[int] = Field(None, description="Max batched tokens")
    trust_remote_code: Optional[bool] = Field(None, description="Trust remote code")
    explanations: dict[str, str] = Field(
        default_factory=dict, description="Parameter explanations"
    )


class PerfEstimate(BaseModel):
    """Approximate performance estimates."""

    decode_toks_per_s_range: tuple[float, float] = Field(
        ..., description="Decode tokens/s range [low, high]"
    )
    prefill_toks_per_s_range: Optional[tuple[float, float]] = Field(
        None, description="Prefill tokens/s range [low, high]"
    )
    ttft_ms_range: Optional[tuple[float, float]] = Field(
        None, description="Time to first token range [low, high] in ms"
    )
    assumptions: list[str] = Field(
        default_factory=list, description="Assumptions used in estimation"
    )


class Artifacts(BaseModel):
    """Generated artifacts."""

    serve_command: str = Field(..., description="vLLM serve command")
    docker_command: Optional[str] = Field(None, description="Docker run command")
    docker_compose: Optional[str] = Field(None, description="docker-compose.yaml content")
    k8s_values: Optional[str] = Field(None, description="Kubernetes values.yaml content")


class PlanResponse(BaseModel):
    """Complete planning response."""

    feasibility: FeasibilityReport = Field(..., description="Feasibility analysis")
    config: VLLMConfig = Field(..., description="Recommended vLLM config")
    performance: PerfEstimate = Field(..., description="Performance estimates")
    artifacts: Artifacts = Field(..., description="Generated artifacts")

    def model_dump_json_pretty(self) -> str:
        """Return pretty-printed JSON."""
        return self.model_dump_json(indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
