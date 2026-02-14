"""Model metadata extraction from local config or HuggingFace Hub."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from huggingface_hub import hf_hub_download
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError


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


def _load_config_from_hf(model_id: str, revision: Optional[str] = None) -> dict[str, Any]:
    """Download and load config.json from HuggingFace Hub."""
    try:
        config_path = hf_hub_download(
            repo_id=model_id,
            filename="config.json",
            revision=revision,
        )
        with open(config_path, "r") as f:
            return json.load(f)
    except RepositoryNotFoundError:
        raise ValueError(f"Model repository not found on HuggingFace: {model_id}")
    except EntryNotFoundError:
        raise ValueError(f"config.json not found in model repository: {model_id}")


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
    """Load model metadata from local path or HuggingFace Hub.

    Args:
        model_id_or_path: Local path to model directory or HuggingFace model ID
        revision: Model revision (branch, tag, commit) for HF models
        trust_remote_code: Whether to trust remote code (not used for config loading)
        params_b: Override parameter count in billions

    Returns:
        ModelMetadata with extracted architecture information

    Raises:
        FileNotFoundError: If local config.json not found
        ValueError: If required fields missing from config
    """
    path = Path(model_id_or_path)

    # Check if it's a local path
    if path.exists() and path.is_dir():
        config_path = path / "config.json"
        config = _load_config_from_path(config_path)
    else:
        # Treat as HuggingFace model ID
        config = _load_config_from_hf(model_id_or_path, revision)

    metadata = _parse_config(config, model_id_or_path)

    # Set parameter count
    if params_b is not None:
        metadata.num_params = int(params_b * 1e9)
    else:
        # Try lookup table first
        known_size = lookup_known_model_size(model_id_or_path)
        if known_size:
            metadata.num_params = int(known_size * 1e9)
        else:
            # Estimate from config
            metadata.num_params = estimate_params_from_config(metadata)

    return metadata
