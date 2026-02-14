"""Profile schema for saving/loading configurations."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from vllm_wizard.schemas.inputs import (
    BatchingMode,
    DType,
    Interconnect,
    KVCacheDType,
    Quantization,
)


class ProfileModel(BaseModel):
    """Model section of profile."""

    id: str = Field(..., description="Model HF id or path")
    revision: Optional[str] = Field(None, description="Model revision")
    dtype: DType = Field(DType.AUTO, description="Weight dtype")
    quantization: Quantization = Field(Quantization.NONE, description="Quantization method")
    kv_cache_dtype: KVCacheDType = Field(KVCacheDType.AUTO, description="KV cache dtype")
    max_model_len: Optional[int] = Field(None, description="Max model length")
    params_b: Optional[float] = Field(None, description="Parameters in billions")


class ProfileHardware(BaseModel):
    """Hardware section of profile."""

    gpu_name: str = Field("auto", description="GPU name")
    gpus: int = Field(1, description="Number of GPUs")
    vram_gb: Optional[float] = Field(None, description="VRAM per GPU in GB")
    interconnect: Interconnect = Field(Interconnect.UNKNOWN, description="Interconnect type")
    tp_size: Optional[int] = Field(None, description="Tensor parallel size")


class ProfileWorkload(BaseModel):
    """Workload section of profile."""

    prompt_tokens: int = Field(512, description="Typical prompt tokens")
    gen_tokens: int = Field(256, description="Typical generation tokens")
    concurrency: int = Field(1, description="Concurrent sequences")
    streaming: bool = Field(True, description="Enable streaming")
    mode: BatchingMode = Field(BatchingMode.BALANCED, description="Batching mode")


class ProfilePolicy(BaseModel):
    """Policy section of profile."""

    gpu_memory_utilization: float = Field(0.90, description="GPU memory utilization")
    overhead_gb: Optional[float] = Field(None, description="Fixed overhead GB")
    fragmentation_factor: float = Field(1.15, description="Fragmentation factor")
    headroom_gb: float = Field(1.0, description="Minimum headroom GB")


class ProfileOutputs(BaseModel):
    """Outputs section of profile."""

    emit: list[str] = Field(
        default_factory=lambda: ["command", "profile"], description="Artifacts to emit"
    )
    vllm_args: dict[str, Any] = Field(default_factory=dict, description="vLLM arguments")


class Profile(BaseModel):
    """Complete profile for saving/loading configurations."""

    profile_version: int = Field(1, description="Profile schema version")
    model: ProfileModel = Field(..., description="Model configuration")
    hardware: ProfileHardware = Field(default_factory=ProfileHardware, description="Hardware config")
    workload: ProfileWorkload = Field(default_factory=ProfileWorkload, description="Workload config")
    policy: ProfilePolicy = Field(default_factory=ProfilePolicy, description="Policy config")
    outputs: ProfileOutputs = Field(default_factory=ProfileOutputs, description="Output config")
