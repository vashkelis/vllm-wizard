"""Command and artifact rendering for vLLM."""

from vllm_wizard.schemas.outputs import VLLMConfig


def render_serve_command(config: VLLMConfig) -> str:
    """Render vLLM serve command.

    Args:
        config: vLLM configuration

    Returns:
        Complete vllm serve command string
    """
    parts = ["vllm", "serve", config.model]

    # Required parameters
    parts.append(f"--tensor-parallel-size {config.tensor_parallel_size}")
    parts.append(f"--dtype {config.dtype}")
    parts.append(f"--gpu-memory-utilization {config.gpu_memory_utilization}")
    parts.append(f"--max-model-len {config.max_model_len}")

    # Optional parameters
    if config.kv_cache_dtype:
        parts.append(f"--kv-cache-dtype {config.kv_cache_dtype}")

    if config.quantization:
        parts.append(f"--quantization {config.quantization}")

    if config.max_num_seqs:
        parts.append(f"--max-num-seqs {config.max_num_seqs}")

    if config.max_num_batched_tokens:
        parts.append(f"--max-num-batched-tokens {config.max_num_batched_tokens}")

    if config.swap_space:
        parts.append(f"--swap-space {config.swap_space}")

    if config.enforce_eager:
        parts.append("--enforce-eager")

    if config.trust_remote_code:
        parts.append("--trust-remote-code")

    return " \\\n  ".join(parts)


def render_docker_command(config: VLLMConfig) -> str:
    """Render docker run command for vLLM.

    Args:
        config: vLLM configuration

    Returns:
        Docker run command string
    """
    # Build vLLM args
    vllm_args = _build_vllm_args(config)

    parts = [
        "docker run",
        "--gpus all",
        "-p 8000:8000",
        "-v $HF_HOME:/root/.cache/huggingface",
        "--ipc=host",
        "vllm/vllm-openai:latest",
        "--model", config.model,
    ]

    parts.extend(vllm_args)

    return " \\\n  ".join(parts)


def render_docker_compose(config: VLLMConfig) -> str:
    """Render docker-compose.yaml for vLLM.

    Args:
        config: vLLM configuration

    Returns:
        docker-compose.yaml content
    """
    # Build command arguments
    vllm_args = _build_vllm_args(config)
    command_args = " ".join(["--model", config.model] + vllm_args)

    # Determine GPU count for reservation
    gpu_count = config.tensor_parallel_size

    compose = f"""version: '3.8'

services:
  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    volumes:
      - ${{HF_HOME:-~/.cache/huggingface}}:/root/.cache/huggingface
    environment:
      - HUGGING_FACE_HUB_TOKEN=${{HUGGING_FACE_HUB_TOKEN:-}}
    ipc: host
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: {gpu_count}
              capabilities: [gpu]
    command: {command_args}
"""

    return compose


def render_k8s_values(config: VLLMConfig) -> str:
    """Render Kubernetes values.yaml snippet for vLLM.

    Args:
        config: vLLM configuration

    Returns:
        Kubernetes values.yaml content
    """
    vllm_args = _build_vllm_args(config)
    args_str = "\n".join([f'    - "{arg}"' for arg in ["--model", config.model] + vllm_args])

    k8s = f"""# vLLM Kubernetes values
# Adjust resources and replicas as needed

replicaCount: 1

image:
  repository: vllm/vllm-openai
  tag: latest
  pullPolicy: IfNotPresent

args:
{args_str}

resources:
  limits:
    nvidia.com/gpu: {config.tensor_parallel_size}
  requests:
    nvidia.com/gpu: {config.tensor_parallel_size}

service:
  type: ClusterIP
  port: 8000

nodeSelector:
  nvidia.com/gpu.present: "true"
"""

    return k8s


def _build_vllm_args(config: VLLMConfig) -> list[str]:
    """Build list of vLLM CLI arguments from config.

    Args:
        config: vLLM configuration

    Returns:
        List of CLI argument strings
    """
    args = [
        f"--tensor-parallel-size {config.tensor_parallel_size}",
        f"--dtype {config.dtype}",
        f"--gpu-memory-utilization {config.gpu_memory_utilization}",
        f"--max-model-len {config.max_model_len}",
    ]

    if config.kv_cache_dtype:
        args.append(f"--kv-cache-dtype {config.kv_cache_dtype}")

    if config.quantization:
        args.append(f"--quantization {config.quantization}")

    if config.max_num_seqs:
        args.append(f"--max-num-seqs {config.max_num_seqs}")

    if config.max_num_batched_tokens:
        args.append(f"--max-num-batched-tokens {config.max_num_batched_tokens}")

    if config.swap_space:
        args.append(f"--swap-space {config.swap_space}")

    if config.enforce_eager:
        args.append("--enforce-eager")

    if config.trust_remote_code:
        args.append("--trust-remote-code")

    return args
