"""Main planner orchestration for vLLM sizing."""

from typing import Optional

from vllm_wizard.hardware.detect import detect_gpus, get_gpu_by_name, recommend_tensor_parallel
from vllm_wizard.models.metadata import load_model_metadata
from vllm_wizard.planning.memory import (
    BYTES_TO_GIB,
    compute_feasibility,
    compute_kv_cache_memory,
    compute_overhead,
    compute_weights_memory,
)
from vllm_wizard.planning.perf import estimate_performance
from vllm_wizard.planning.recommend import generate_recommendations
from vllm_wizard.render.commands import render_docker_compose, render_docker_command, render_serve_command
from vllm_wizard.schemas.inputs import PlanRequest
from vllm_wizard.schemas.outputs import Artifacts, GPUInfo, PlanResponse


def run_plan(request: PlanRequest) -> PlanResponse:
    """Run the complete planning pipeline.

    Args:
        request: Complete planning request

    Returns:
        PlanResponse with feasibility, config, performance, and artifacts
    """
    # 1. Load model metadata
    metadata = load_model_metadata(
        model_id_or_path=request.model.model,
        revision=request.model.revision,
        trust_remote_code=request.model.trust_remote_code,
        params_b=request.model.params_b,
    )

    # 2. Detect or configure hardware
    gpus = _resolve_hardware(request)

    if not gpus:
        raise ValueError(
            "No GPUs detected or specified. "
            "Provide --gpu and --vram-gb flags, or run on a system with nvidia-smi."
        )

    # 3. Calculate total VRAM
    vram_total_bytes = sum(gpu.vram_mib * 1024 * 1024 for gpu in gpus)
    tp_size = request.hardware.tensor_parallel_size or recommend_tensor_parallel(gpus)

    # For TP, we use VRAM per GPU group
    effective_vram = (vram_total_bytes // len(gpus)) * tp_size

    # 4. Compute memory breakdown
    params_b = request.model.params_b or (metadata.num_params / 1e9 if metadata.num_params else 7.0)

    weights_bytes = compute_weights_memory(
        params_b=params_b,
        dtype=request.model.dtype,
        quantization=request.model.quantization,
    )

    # Weights per GPU with TP
    weights_per_tp = weights_bytes // tp_size

    context_len = request.model.max_model_len or metadata.max_position_embeddings

    kv_cache_bytes = compute_kv_cache_memory(
        metadata=metadata,
        context_len=context_len,
        concurrency=request.workload.concurrency,
        kv_dtype=request.model.kv_cache_dtype,
        dtype=request.model.dtype,
        fragmentation_factor=request.policy.fragmentation_factor,
    )

    overhead_bytes = compute_overhead(
        vram_total_bytes=effective_vram,
        tp_size=tp_size,
        fixed_overhead_gb=request.policy.overhead_gb,
    )

    # 5. Compute feasibility
    feasibility = compute_feasibility(
        weights_bytes=weights_per_tp,
        kv_cache_bytes=kv_cache_bytes,
        overhead_bytes=overhead_bytes,
        vram_total_bytes=effective_vram,
        gpu_memory_utilization=request.policy.gpu_memory_utilization,
        headroom_gb=request.policy.headroom_gb,
        context_len=context_len,
        concurrency=request.workload.concurrency,
        metadata=metadata,
        kv_dtype=request.model.kv_cache_dtype,
        dtype=request.model.dtype,
        fragmentation_factor=request.policy.fragmentation_factor,
    )

    # 6. Generate recommendations
    config = generate_recommendations(
        request=request,
        metadata=metadata,
        gpus=gpus,
        vram_total_bytes=vram_total_bytes,
    )

    # 7. Estimate performance
    performance = estimate_performance(
        gpu_name=gpus[0].name,
        params_b=params_b,
        tp_size=config.tensor_parallel_size,
        context_len=config.max_model_len,
        prompt_tokens=request.workload.prompt_tokens,
        quantization=request.model.quantization,
        interconnect=request.hardware.interconnect,
        num_gpus=len(gpus),
    )

    # 8. Generate artifacts
    serve_command = render_serve_command(config)
    docker_command = render_docker_command(config)
    docker_compose = render_docker_compose(config)

    artifacts = Artifacts(
        serve_command=serve_command,
        docker_command=docker_command,
        docker_compose=docker_compose,
    )

    return PlanResponse(
        feasibility=feasibility,
        config=config,
        performance=performance,
        artifacts=artifacts,
    )


def _resolve_hardware(request: PlanRequest) -> list[GPUInfo]:
    """Resolve hardware configuration from request or detection.

    Args:
        request: Planning request

    Returns:
        List of GPUInfo objects
    """
    hardware = request.hardware

    # Auto-detect if requested
    if hardware.gpu.lower() == "auto":
        detected = detect_gpus()
        if detected:
            # Limit to requested number of GPUs
            return detected[: hardware.gpus]

    # Try to get GPU by name
    if hardware.gpu.lower() != "auto":
        gpu = get_gpu_by_name(hardware.gpu)
        if gpu:
            return [gpu] * hardware.gpus

    # Fall back to manual specification
    if hardware.vram_gb:
        vram_mib = int(hardware.vram_gb * 1024)
        gpu = GPUInfo(
            name=hardware.gpu if hardware.gpu != "auto" else "Unknown GPU",
            vram_mib=vram_mib,
        )
        return [gpu] * hardware.gpus

    return []
