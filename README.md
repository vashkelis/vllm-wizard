# vLLM Config Wizard

A CLI tool for vLLM configuration generation and GPU sizing. Given your model, hardware, and workload requirements, vLLM Wizard generates optimized configurations with VRAM feasibility analysis and approximate performance estimates.

## Features

- **VRAM Feasibility Analysis**: Calculate if your model fits in GPU memory with detailed breakdowns
- **Configuration Generation**: Generate optimized `vllm serve` commands, docker-compose files, and YAML profiles
- **Performance Estimation**: Get approximate throughput and latency estimates (clearly labeled as heuristic)
- **GPU Detection**: Auto-detect NVIDIA GPUs via nvidia-smi
- **Profile Support**: Save and load configurations as YAML profiles

## Installation

```bash
# Install from source
pip install -e .

# With development dependencies
pip install -e ".[dev]"

# With web UI support (optional)
pip install -e ".[web]"
```

## Quick Start

### Detect GPUs

```bash
# Detect available GPUs
vllm-wizard detect

# JSON output
vllm-wizard detect --json
```

### Plan Configuration

```bash
# Basic planning with auto GPU detection
vllm-wizard plan --model meta-llama/Llama-2-7b-hf

# Specify hardware manually
vllm-wizard plan --model meta-llama/Llama-2-7b-hf \
  --gpu "RTX 4090" \
  --gpus 1 \
  --vram-gb 24

# With workload parameters
vllm-wizard plan --model meta-llama/Llama-2-7b-hf \
  --gpu "A100 80GB" \
  --prompt-tokens 1024 \
  --gen-tokens 512 \
  --concurrency 8

# JSON output for scripting
vllm-wizard plan --model meta-llama/Llama-2-7b-hf --json

# Include explanations for each parameter
vllm-wizard plan --model meta-llama/Llama-2-7b-hf --explain
```

### Generate Artifacts

```bash
# Generate serve command and profile
vllm-wizard generate \
  --output-dir ./vllm-config \
  --model meta-llama/Llama-2-7b-hf \
  --gpu "A100 80GB"

# Include docker-compose
vllm-wizard generate \
  --output-dir ./vllm-config \
  --model meta-llama/Llama-2-7b-hf \
  --emit command,profile,compose
```

### Using Profiles

```bash
# Generate from a profile
vllm-wizard plan --profile ./my-config.yaml

# Load and regenerate artifacts
vllm-wizard generate --output-dir ./output --profile ./my-config.yaml
```

## Command Reference

### `vllm-wizard detect`

Detect and display available NVIDIA GPUs.

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |

### `vllm-wizard plan`

Compute feasibility, recommendations, and performance estimates.

**Model Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--model, -m` | HuggingFace model ID or local path | Required |
| `--revision` | Model revision/branch | None |
| `--dtype` | Weight dtype (auto, fp16, bf16, fp32) | auto |
| `--quantization, -q` | Quantization (none, awq, gptq, int8, fp8) | none |
| `--kv-cache-dtype` | KV cache dtype | auto |
| `--max-model-len` | Target context length | Model max |
| `--params-b` | Model parameters in billions (override) | Auto |

**Hardware Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--gpu` | GPU name or "auto" | auto |
| `--gpus` | Number of GPUs | 1 |
| `--vram-gb` | VRAM per GPU in GB | Auto |
| `--tensor-parallel-size, --tp` | Tensor parallel size | Auto |
| `--interconnect` | GPU interconnect (pcie, nvlink) | unknown |

**Workload Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--prompt-tokens` | Typical prompt length | 512 |
| `--gen-tokens` | Typical generation length | 256 |
| `--concurrency, -c` | Concurrent sequences | 1 |
| `--batching-mode` | throughput, latency, balanced | balanced |

**Policy Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--gpu-memory-utilization` | GPU memory target (0.5-0.98) | 0.90 |
| `--overhead-gb` | Fixed overhead in GB | Auto |
| `--fragmentation-factor` | KV cache fragmentation | 1.15 |
| `--headroom-gb` | Minimum headroom | 1.0 |

**Output Options:**
| Option | Description |
|--------|-------------|
| `--profile, -p` | Load from YAML profile |
| `--json` | Output as JSON |
| `--explain` | Include parameter explanations |

### `vllm-wizard generate`

Generate configuration artifacts to disk.

All options from `plan` plus:

| Option | Description | Default |
|--------|-------------|---------|
| `--output-dir, -o` | Output directory | Required |
| `--emit` | Artifacts to emit (comma-separated) | command,profile |

Emit options: `command`, `profile`, `compose`, `k8s`

## Understanding the Output

### VRAM Breakdown

The VRAM breakdown shows how GPU memory is allocated:

- **Model Weights**: Memory for model parameters (depends on dtype/quantization)
- **KV Cache**: Memory for attention key-value cache (scales with context × concurrency)
- **Overhead**: Framework overhead and communication buffers
- **Headroom**: Available buffer for runtime allocations

### OOM Risk Levels

- **LOW**: >= 2 GiB headroom, safe to run
- **MEDIUM**: 0-2 GiB headroom, may work but monitor closely
- **HIGH**: Negative headroom, likely OOM - consider quantization or reducing context

### Performance Estimates

**Important**: Performance estimates are heuristic approximations based on:
- GPU baseline performance tables
- Scaling factors for model size, tensor parallelism, and context length
- Quantization speedup factors

**These are NOT benchmarks.** Actual performance depends on:
- vLLM version and kernel selection
- CUDA/driver versions
- Batch sizes and request patterns
- Prompt/generation ratio

Always benchmark your specific workload before production deployment.

## Memory Model

### Weights Memory

```
weights_bytes = parameters × bytes_per_param

Bytes per parameter:
- FP32: 4.0
- FP16/BF16: 2.0
- INT8: 1.0
- AWQ/GPTQ (4-bit): ~0.55 (includes overhead)
```

### KV Cache Memory

```
kv_per_token_per_layer = 2 × num_kv_heads × head_dim × dtype_bytes
kv_cache = kv_per_token_per_layer × num_layers × context_len × concurrency × fragmentation_factor
```

With GQA (grouped-query attention), `num_kv_heads` is typically smaller than `num_attention_heads`, significantly reducing KV cache size.

## Profile Format

Profiles use YAML with this schema:

```yaml
profile_version: 1
model:
  id: "meta-llama/Llama-2-7b-hf"
  dtype: "auto"
  quantization: "none"
  max_model_len: 4096
hardware:
  gpu_name: "A100 80GB"
  gpus: 1
  interconnect: "unknown"
workload:
  prompt_tokens: 512
  gen_tokens: 256
  concurrency: 4
  mode: "balanced"
policy:
  gpu_memory_utilization: 0.90
  fragmentation_factor: 1.15
  headroom_gb: 1.0
```

## Examples

### Single GPU Configuration

```bash
# LLaMA 2 7B on RTX 4090
vllm-wizard plan \
  --model meta-llama/Llama-2-7b-hf \
  --gpu "RTX 4090" \
  --max-model-len 4096 \
  --concurrency 2
```

### Multi-GPU with Tensor Parallelism

```bash
# LLaMA 2 70B on 4x A100 80GB
vllm-wizard plan \
  --model meta-llama/Llama-2-70b-hf \
  --gpu "A100 80GB" \
  --gpus 4 \
  --tensor-parallel-size 4 \
  --interconnect nvlink \
  --max-model-len 4096
```

### Quantized Model

```bash
# 70B model with AWQ on single GPU
vllm-wizard plan \
  --model TheBloke/Llama-2-70B-AWQ \
  --gpu "RTX 4090" \
  --quantization awq \
  --max-model-len 2048
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=vllm_wizard

# Lint
ruff check src/
```

## License

APACHE 2.0

## Disclaimer

This tool provides **estimates and recommendations**, not guarantees. Always:

1. Test configurations on your actual hardware
2. Monitor VRAM usage during model loading
3. Benchmark throughput/latency for your specific workload
4. Start with conservative settings and adjust based on results

Performance estimates are heuristic approximations and should not be used for capacity planning without real benchmarks.
