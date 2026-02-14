"""Planning module for VRAM calculations and recommendations."""

from vllm_wizard.planning.memory import (
    DTYPE_BYTES,
    compute_feasibility,
    compute_kv_cache_memory,
    compute_max_concurrency_at_context,
    compute_max_context_at_concurrency,
    compute_overhead,
    compute_weights_memory,
)
from vllm_wizard.planning.perf import estimate_performance
from vllm_wizard.planning.planner import run_plan
from vllm_wizard.planning.recommend import generate_recommendations

__all__ = [
    # Memory
    "DTYPE_BYTES",
    "compute_weights_memory",
    "compute_kv_cache_memory",
    "compute_overhead",
    "compute_feasibility",
    "compute_max_concurrency_at_context",
    "compute_max_context_at_concurrency",
    # Perf
    "estimate_performance",
    # Recommend
    "generate_recommendations",
    # Planner
    "run_plan",
]
