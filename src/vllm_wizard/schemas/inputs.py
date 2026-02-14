"""Input schemas for vLLM Wizard."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DType(str, Enum):
    """Data type for model weights."""

    AUTO = "auto"
    FP16 = "fp16"
    BF16 = "bf16"
    FP32 = "fp32"


class Quantization(str, Enum):
    """Quantization method."""

    NONE = "none"
    AWQ = "awq"
    GPTQ = "gptq"
    INT8 = "int8"
    FP8 = "fp8"


class KVCacheDType(str, Enum):
    """KV cache data type."""

    AUTO = "auto"
    FP16 = "fp16"
    BF16 = "bf16"
    FP8_E4M3FN = "fp8_e4m3fn"
    FP8_E5M2 = "fp8_e5m2"


class Interconnect(str, Enum):
    """GPU interconnect type."""

    PCIE = "pcie"
    NVLINK = "nvlink"
    UNKNOWN = "unknown"


class BatchingMode(str, Enum):
    """Batching optimization mode."""

    THROUGHPUT = "throughput"
    LATENCY = "latency"
    BALANCED = "balanced"


class ModelInput(BaseModel):
    """Model configuration inputs."""

    model: str = Field(..., description="HF model id or local path")
    revision: Optional[str] = Field(None, description="Model revision/branch")
    trust_remote_code: bool = Field(False, description="Trust remote code from HF")
    dtype: DType = Field(DType.AUTO, description="Model weight dtype")
    quantization: Quantization = Field(Quantization.NONE, description="Quantization method")
    kv_cache_dtype: KVCacheDType = Field(KVCacheDType.AUTO, description="KV cache dtype")
    max_model_len: Optional[int] = Field(None, description="Target context length", gt=0)
    tokenizer: Optional[str] = Field(None, description="Tokenizer override")
    params_b: Optional[float] = Field(None, description="Model parameters in billions", gt=0)


class HardwareInput(BaseModel):
    """Hardware configuration inputs."""

    gpu: str = Field("auto", description="GPU name or 'auto' for detection")
    gpus: int = Field(1, description="Number of GPUs", ge=1)
    vram_gb: Optional[float] = Field(None, description="VRAM per GPU in GB", gt=0)
    interconnect: Interconnect = Field(Interconnect.UNKNOWN, description="GPU interconnect type")
    tensor_parallel_size: Optional[int] = Field(None, description="Tensor parallel size", ge=1)


class WorkloadInput(BaseModel):
    """Workload configuration inputs."""

    prompt_tokens: int = Field(512, description="Typical prompt token count", ge=1)
    gen_tokens: int = Field(256, description="Typical generation token count", ge=1)
    concurrency: int = Field(1, description="Simultaneous sequences", ge=1)
    target_latency_ms: Optional[float] = Field(None, description="Target latency in ms", gt=0)
    streaming: bool = Field(True, description="Enable streaming responses")
    batching_mode: BatchingMode = Field(BatchingMode.BALANCED, description="Batching mode")


class PolicyInput(BaseModel):
    """Policy and safety margin inputs."""

    gpu_memory_utilization: float = Field(
        0.90, description="GPU memory utilization target", ge=0.5, le=0.98
    )
    overhead_gb: Optional[float] = Field(None, description="Fixed overhead in GB", ge=0)
    fragmentation_factor: float = Field(
        1.15, description="KV cache fragmentation factor", ge=1.0, le=2.0
    )
    headroom_gb: float = Field(1.0, description="Minimum headroom in GB", ge=0)


class PlanRequest(BaseModel):
    """Complete planning request combining all inputs."""

    model: ModelInput
    hardware: HardwareInput = Field(default_factory=HardwareInput)
    workload: WorkloadInput = Field(default_factory=WorkloadInput)
    policy: PolicyInput = Field(default_factory=PolicyInput)
    explain: bool = Field(False, description="Include explanations for recommendations")
