"""Profile loading and saving."""

from pathlib import Path
from typing import Any, Optional

import yaml

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
from vllm_wizard.schemas.profile import (
    Profile,
    ProfileHardware,
    ProfileModel,
    ProfileOutputs,
    ProfilePolicy,
    ProfileWorkload,
)


def save_profile(profile: Profile, path: Path) -> None:
    """Save profile to YAML file.

    Args:
        profile: Profile to save
        path: Output file path
    """
    # Convert to dict with proper enum handling
    data = profile.model_dump(mode="json")

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_profile(path: Path) -> Profile:
    """Load profile from YAML file.

    Args:
        path: Profile file path

    Returns:
        Loaded Profile object

    Raises:
        FileNotFoundError: If profile file doesn't exist
        ValueError: If profile is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return Profile(**data)


def profile_to_request(profile: Profile) -> PlanRequest:
    """Convert a Profile to a PlanRequest.

    Args:
        profile: Profile loaded from YAML

    Returns:
        PlanRequest for the planner
    """
    model_input = ModelInput(
        model=profile.model.id,
        revision=profile.model.revision,
        dtype=profile.model.dtype,
        quantization=profile.model.quantization,
        kv_cache_dtype=profile.model.kv_cache_dtype,
        max_model_len=profile.model.max_model_len,
        params_b=profile.model.params_b,
    )

    hardware_input = HardwareInput(
        gpu=profile.hardware.gpu_name,
        gpus=profile.hardware.gpus,
        vram_gb=profile.hardware.vram_gb,
        interconnect=profile.hardware.interconnect,
        tensor_parallel_size=profile.hardware.tp_size,
    )

    workload_input = WorkloadInput(
        prompt_tokens=profile.workload.prompt_tokens,
        gen_tokens=profile.workload.gen_tokens,
        concurrency=profile.workload.concurrency,
        streaming=profile.workload.streaming,
        batching_mode=profile.workload.mode,
    )

    policy_input = PolicyInput(
        gpu_memory_utilization=profile.policy.gpu_memory_utilization,
        overhead_gb=profile.policy.overhead_gb,
        fragmentation_factor=profile.policy.fragmentation_factor,
        headroom_gb=profile.policy.headroom_gb,
    )

    return PlanRequest(
        model=model_input,
        hardware=hardware_input,
        workload=workload_input,
        policy=policy_input,
    )


def request_to_profile(request: PlanRequest, emit: Optional[list[str]] = None) -> Profile:
    """Convert a PlanRequest to a Profile for saving.

    Args:
        request: Planning request
        emit: List of artifacts to emit

    Returns:
        Profile for saving
    """
    profile_model = ProfileModel(
        id=request.model.model,
        revision=request.model.revision,
        dtype=request.model.dtype,
        quantization=request.model.quantization,
        kv_cache_dtype=request.model.kv_cache_dtype,
        max_model_len=request.model.max_model_len,
        params_b=request.model.params_b,
    )

    profile_hardware = ProfileHardware(
        gpu_name=request.hardware.gpu,
        gpus=request.hardware.gpus,
        vram_gb=request.hardware.vram_gb,
        interconnect=request.hardware.interconnect,
        tp_size=request.hardware.tensor_parallel_size,
    )

    profile_workload = ProfileWorkload(
        prompt_tokens=request.workload.prompt_tokens,
        gen_tokens=request.workload.gen_tokens,
        concurrency=request.workload.concurrency,
        streaming=request.workload.streaming,
        mode=request.workload.batching_mode,
    )

    profile_policy = ProfilePolicy(
        gpu_memory_utilization=request.policy.gpu_memory_utilization,
        overhead_gb=request.policy.overhead_gb,
        fragmentation_factor=request.policy.fragmentation_factor,
        headroom_gb=request.policy.headroom_gb,
    )

    profile_outputs = ProfileOutputs(
        emit=emit or ["command", "profile"],
    )

    return Profile(
        profile_version=1,
        model=profile_model,
        hardware=profile_hardware,
        workload=profile_workload,
        policy=profile_policy,
        outputs=profile_outputs,
    )
