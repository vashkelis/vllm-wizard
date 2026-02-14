"""Pytest fixtures for vLLM Wizard tests."""

import json
from pathlib import Path

import pytest

from vllm_wizard.models.metadata import ModelMetadata


@pytest.fixture
def llama_config() -> dict:
    """Sample LLaMA-style model config."""
    return {
        "architectures": ["LlamaForCausalLM"],
        "model_type": "llama",
        "hidden_size": 4096,
        "intermediate_size": 11008,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "num_key_value_heads": 32,
        "vocab_size": 32000,
        "max_position_embeddings": 4096,
        "rms_norm_eps": 1e-6,
        "torch_dtype": "float16",
    }


@pytest.fixture
def llama_gqa_config() -> dict:
    """Sample LLaMA config with GQA (fewer KV heads)."""
    return {
        "architectures": ["LlamaForCausalLM"],
        "model_type": "llama",
        "hidden_size": 4096,
        "intermediate_size": 14336,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "num_key_value_heads": 8,  # GQA
        "vocab_size": 128256,
        "max_position_embeddings": 8192,
        "rms_norm_eps": 1e-5,
        "torch_dtype": "bfloat16",
    }


@pytest.fixture
def config_no_kv_heads() -> dict:
    """Config without num_key_value_heads (MHA model)."""
    return {
        "architectures": ["LlamaForCausalLM"],
        "model_type": "llama",
        "hidden_size": 4096,
        "intermediate_size": 11008,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        # No num_key_value_heads - should fallback to num_attention_heads
        "vocab_size": 32000,
        "max_position_embeddings": 4096,
    }


@pytest.fixture
def mistral_config() -> dict:
    """Sample Mistral config."""
    return {
        "architectures": ["MistralForCausalLM"],
        "model_type": "mistral",
        "hidden_size": 4096,
        "intermediate_size": 14336,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "num_key_value_heads": 8,
        "vocab_size": 32000,
        "max_position_embeddings": 32768,
        "sliding_window": 4096,
    }


@pytest.fixture
def llama_metadata() -> ModelMetadata:
    """Pre-built ModelMetadata for a 7B LLaMA-like model."""
    return ModelMetadata(
        num_hidden_layers=32,
        hidden_size=4096,
        num_attention_heads=32,
        num_key_value_heads=32,
        vocab_size=32000,
        max_position_embeddings=4096,
        model_type="llama",
        intermediate_size=11008,
        num_params=7_000_000_000,
    )


@pytest.fixture
def llama_8b_metadata() -> ModelMetadata:
    """Pre-built ModelMetadata for LLaMA 3 8B with GQA."""
    return ModelMetadata(
        num_hidden_layers=32,
        hidden_size=4096,
        num_attention_heads=32,
        num_key_value_heads=8,  # GQA
        vocab_size=128256,
        max_position_embeddings=8192,
        model_type="llama",
        intermediate_size=14336,
        num_params=8_000_000_000,
    )


@pytest.fixture
def tmp_config_dir(tmp_path: Path, llama_config: dict) -> Path:
    """Create a temporary directory with a config.json file."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(llama_config))
    return tmp_path


@pytest.fixture
def tmp_config_no_kv(tmp_path: Path, config_no_kv_heads: dict) -> Path:
    """Create a temporary directory with config missing KV heads."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config_no_kv_heads))
    return tmp_path
