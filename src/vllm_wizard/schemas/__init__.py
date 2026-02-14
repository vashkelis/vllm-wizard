"""Pydantic schemas for vLLM Wizard."""

from vllm_wizard.schemas.inputs import (
    BatchingMode,
    DType,
    HardwareInput,
    Interconnect,
    KVCacheDType,
    ModelInput,
    PlanRequest,
    PolicyInput,
    Quantization,
    WorkloadInput,
)
from vllm_wizard.schemas.outputs import (
    Artifacts,
    FeasibilityReport,
    GPUInfo,
    OOMRisk,
    PerfEstimate,
    PlanResponse,
    VLLMConfig,
)
from vllm_wizard.schemas.profile import Profile

__all__ = [
    # Inputs
    "ModelInput",
    "HardwareInput",
    "WorkloadInput",
    "PolicyInput",
    "PlanRequest",
    # Enums
    "DType",
    "Quantization",
    "KVCacheDType",
    "Interconnect",
    "BatchingMode",
    "OOMRisk",
    # Outputs
    "GPUInfo",
    "FeasibilityReport",
    "VLLMConfig",
    "PerfEstimate",
    "Artifacts",
    "PlanResponse",
    # Profile
    "Profile",
]
