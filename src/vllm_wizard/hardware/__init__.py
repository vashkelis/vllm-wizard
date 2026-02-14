"""Hardware detection module."""

from vllm_wizard.hardware.detect import detect_gpus, recommend_tensor_parallel

__all__ = [
    "detect_gpus",
    "recommend_tensor_parallel",
]
