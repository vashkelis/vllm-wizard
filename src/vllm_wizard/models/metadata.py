"""Model metadata extraction - offline estimation."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ModelMetadata:
    """Extracted model architecture metadata for memory calculations."""

    num_hidden_layers: int
    hidden_size: int
    num_attention_heads: int
    num_key_value_heads: int
    vocab_size: int
    max_position_embeddings: int
    model_type: str
    intermediate_size: Optional[int] = None
    num_params: Optional[int] = None

    @property
    def head_dim(self) -> int:
        """Compute head dimension."""
        return self.hidden_size // self.num_attention_heads

    @property
    def params_billions(self) -> Optional[float]:
        """Return parameters in billions if known."""
        if self.num_params:
            return self.num_params / 1e9
        return None


# Known model size lookup table (approximate parameters in billions)
KNOWN_MODEL_SIZES: dict[str, float] = {
    "llama-2-7b": 7.0,
    "llama-2-13b": 13.0,
    "llama-2-70b": 70.0,
    "llama-3-8b": 8.0,
    "llama-3-70b": 70.0,
    "llama-3.1-8b": 8.0,
    "llama-3.1-70b": 70.0,
    "llama-3.1-405b": 405.0,
    "mistral-7b": 7.0,
    "mixtral-8x7b": 46.7,
    "mixtral-8x22b": 141.0,
    "qwen-7b": 7.0,
    "qwen-14b": 14.0,
    "qwen-72b": 72.0,
    "qwen2-7b": 7.0,
    "qwen2-72b": 72.0,
    "gemma-2b": 2.5,
    "gemma-7b": 8.5,
    "phi-2": 2.7,
    "phi-3-mini": 3.8,
    "phi-3-small": 7.0,
    "phi-3-medium": 14.0,
    "falcon-7b": 7.0,
    "falcon-40b": 40.0,
    "falcon-180b": 180.0,
    "yi-6b": 6.0,
    "yi-34b": 34.0,
    "deepseek-7b": 7.0,
    "deepseek-67b": 67.0,
    "deepseek-v2": 236.0,
    "codellama-7b": 7.0,
    "codellama-13b": 13.0,
    "codellama-34b": 34.0,
}


def _load_config_from_path(config_path: Path) -> dict[str, Any]:
    """Load config.json from a local path."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        return json.load(f)


def _parse_config(config: dict[str, Any], model_id: str) -> ModelMetadata:
    """Parse model config.json into ModelMetadata."""
    model_type = config.get("model_type", "unknown")

    # Extract architecture parameters with fallbacks for different model families
    num_hidden_layers = config.get(
        "num_hidden_layers", config.get("n_layer", config.get("num_layers"))
    )
    if num_hidden_layers is None:
        raise ValueError(
            f"Cannot determine num_hidden_layers from config. "
            f"Ensure config.json contains 'num_hidden_layers', 'n_layer', or 'num_layers'."
        )

    hidden_size = config.get("hidden_size", config.get("n_embd", config.get("d_model")))
    if hidden_size is None:
        raise ValueError(
            f"Cannot determine hidden_size from config. "
            f"Ensure config.json contains 'hidden_size', 'n_embd', or 'd_model'."
        )

    num_attention_heads = config.get(
        "num_attention_heads", config.get("n_head", config.get("num_heads"))
    )
    if num_attention_heads is None:
        raise ValueError(
            f"Cannot determine num_attention_heads from config. "
            f"Ensure config.json contains 'num_attention_heads', 'n_head', or 'num_heads'."
        )

    # KV heads: fallback to attention heads if not specified (MHA models)
    num_key_value_heads = config.get(
        "num_key_value_heads",
        config.get("num_kv_heads", config.get("n_head_kv", num_attention_heads)),
    )

    vocab_size = config.get("vocab_size", 32000)

    max_position_embeddings = config.get(
        "max_position_embeddings",
        config.get("max_seq_len", config.get("n_positions", config.get("seq_length", 4096))),
    )

    intermediate_size = config.get(
        "intermediate_size", config.get("ffn_dim", config.get("n_inner"))
    )

    return ModelMetadata(
        num_hidden_layers=num_hidden_layers,
        hidden_size=hidden_size,
        num_attention_heads=num_attention_heads,
        num_key_value_heads=num_key_value_heads,
        vocab_size=vocab_size,
        max_position_embeddings=max_position_embeddings,
        model_type=model_type,
        intermediate_size=intermediate_size,
    )


def estimate_params_from_config(metadata: ModelMetadata) -> int:
    """Estimate total parameters from model architecture.

    This is a rough estimate based on typical transformer architecture.
    For accurate counts, use the model's reported parameter count or safetensors index.
    """
    # Embedding layers
    embed_params = metadata.vocab_size * metadata.hidden_size * 2  # input + output embeddings

    # Per-layer parameters (approximate for standard transformer)
    # QKV projection
    qkv_params = metadata.hidden_size * metadata.hidden_size * 3  # Q, K, V projections

    # Output projection
    out_proj_params = metadata.hidden_size * metadata.hidden_size

    # MLP (assuming intermediate_size or 4x hidden_size)
    intermediate = metadata.intermediate_size or (4 * metadata.hidden_size)
    mlp_params = 2 * metadata.hidden_size * intermediate  # up + down projections

    # Layer norms (small)
    ln_params = 4 * metadata.hidden_size  # 2 layer norms per block

    per_layer_params = qkv_params + out_proj_params + mlp_params + ln_params

    total_params = embed_params + (per_layer_params * metadata.num_hidden_layers)

    return total_params


def lookup_known_model_size(model_id: str) -> Optional[float]:
    """Look up model size from known model table.

    Args:
        model_id: Model ID or path

    Returns:
        Parameters in billions if found, None otherwise
    """
    model_lower = model_id.lower()

    for key, params_b in KNOWN_MODEL_SIZES.items():
        if key in model_lower:
            return params_b

    return None


def load_model_metadata(
    model_id_or_path: str,
    revision: Optional[str] = None,
    trust_remote_code: bool = False,
    params_b: Optional[float] = None,
) -> ModelMetadata:
    """Load model metadata from local path or estimate from known model families.

    This function does NOT download models from HuggingFace. For VRAM estimation,
    we only need the parameter count which can be provided via --params-b or
    looked up from known model sizes.

    Args:
        model_id_or_path: Model identifier (used for size lookup)
        revision: Ignored (kept for API compatibility)
        trust_remote_code: Ignored (kept for API compatibility)
        params_b: Parameter count in billions. If provided, skips HF download.

    Returns:
        ModelMetadata with extracted architecture information
    """
    # If params_b is provided or can be looked up, use estimated config
    if params_b is None:
        params_b = lookup_known_model_size(model_id_or_path)

    if params_b is not None:
        # Generate estimated config based on parameter count
        config = _estimate_config_from_params(params_b)
    else:
        # Try to load from local path
        path = Path(model_id_or_path)
        if path.exists() and path.is_dir():
            config_path = path / "config.json"
            if config_path.exists():
                config = _load_config_from_path(config_path)
            else:
                raise FileNotFoundError(
                    f"config.json not found in {path}. "
                    f"Provide --params-b to estimate without config file."
                )
        else:
            # Unknown model without params - use a safe default
            raise ValueError(
                f"Cannot determine model parameters for '{model_id_or_path}'.\n"
                f"Please provide --params-b (e.g., --params-b 7 for 7B model)."
            )

    metadata = _parse_config(config, model_id_or_path)

    # Set parameter count
    if params_b is not None:
        metadata.num_params = int(params_b * 1e9)
    else:
        # Estimate from config
        metadata.num_params = estimate_params_from_config(metadata)

    return metadata


def _estimate_config_from_params(params_b: float) -> dict[str, Any]:
    """Estimate model config from parameter count.
    
    Uses typical LLaMA-family architecture patterns.
    """
    # Default 7B config
    config = {
        "model_type": "llama",
        "num_hidden_layers": 32,
        "hidden_size": 4096,
        "num_attention_heads": 32,
        "num_key_value_heads": 32,
        "vocab_size": 32000,
        "max_position_embeddings": 4096,
        "intermediate_size": 11008,
    }

    # Scale based on parameter count
    if params_b >= 400:
        # 400B+ (e.g., LLaMA 3.1 405B)
        config.update({
            "num_hidden_layers": 126,
            "hidden_size": 16384,
            "num_attention_heads": 128,
            "num_key_value_heads": 128,
            "vocab_size": 128256,
            "max_position_embeddings": 131072,
            "intermediate_size": 53248,
        })
    elif params_b >= 70:
        # 70B (e.g., LLaMA 2 70B)
        config.update({
            "num_hidden_layers": 80,
            "hidden_size": 8192,
            "num_attention_heads": 64,
            "num_key_value_heads": 8,  # GQA
            "vocab_size": 32000,
            "max_position_embeddings": 4096,
            "intermediate_size": 28672,
        })
    elif params_b >= 30:
        # 30-70B (e.g., Mixtral 8x22B ~141B total, Qwen 72B)
        config.update({
            "num_hidden_layers": 60,
            "hidden_size": 6144,
            "num_attention_heads": 48,
            "num_key_value_heads": 8,
            "vocab_size": 151936,
            "max_position_embeddings": 32768,
            "intermediate_size": 16384,
        })
    elif params_b >= 13:
        # 13B (e.g., LLaMA 2 13B)
        config.update({
            "num_hidden_layers": 40,
            "hidden_size": 5120,
            "num_attention_heads": 40,
            "num_key_value_heads": 40,
            "vocab_size": 32000,
            "max_position_embeddings": 4096,
            "intermediate_size": 13824,
        })
    elif params_b >= 3:
        # 3-7B (e.g., LLaMA 2 7B, Mistral 7B)
        config.update({
            "num_hidden_layers": 32,
            "hidden_size": 4096,
            "num_attention_heads": 32,
            "num_key_value_heads": 8,  # GQA common in this range
            "vocab_size": 32000,
            "max_position_embeddings": 8192,
            "intermediate_size": 14336,
        })
    else:
        # <3B (e.g., Phi-2, Gemma 2B)
        config.update({
            "num_hidden_layers": 28,
            "hidden_size": 2560,
            "num_attention_heads": 20,
            "num_key_value_heads": 20,
            "vocab_size": 51200,
            "max_position_embeddings": 2048,
            "intermediate_size": 10240,
        })

    return config
