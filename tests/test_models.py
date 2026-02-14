"""Tests for model metadata extraction."""

import json
from pathlib import Path

import pytest

from vllm_wizard.models.metadata import (
    ModelMetadata,
    estimate_params_from_config,
    load_model_metadata,
    lookup_known_model_size,
)


class TestLoadModelMetadata:
    """Tests for load_model_metadata function."""

    def test_load_from_local_path(self, tmp_config_dir: Path):
        """Test loading metadata from local config.json."""
        metadata = load_model_metadata(str(tmp_config_dir))

        assert metadata.num_hidden_layers == 32
        assert metadata.hidden_size == 4096
        assert metadata.num_attention_heads == 32
        assert metadata.num_key_value_heads == 32
        assert metadata.vocab_size == 32000
        assert metadata.max_position_embeddings == 4096
        assert metadata.model_type == "llama"

    def test_fallback_kv_heads(self, tmp_config_no_kv: Path):
        """Test fallback when num_key_value_heads is missing."""
        metadata = load_model_metadata(str(tmp_config_no_kv))

        # Should fallback to num_attention_heads
        assert metadata.num_key_value_heads == metadata.num_attention_heads
        assert metadata.num_key_value_heads == 32

    def test_head_dim_property(self, llama_metadata: ModelMetadata):
        """Test head_dim computed property."""
        # head_dim = hidden_size / num_attention_heads = 4096 / 32 = 128
        assert llama_metadata.head_dim == 128

    def test_params_billions_property(self, llama_metadata: ModelMetadata):
        """Test params_billions property."""
        assert llama_metadata.params_billions == 7.0

    def test_missing_required_field(self, tmp_path: Path):
        """Test error when required fields are missing."""
        # Config without num_hidden_layers
        config = {
            "model_type": "llama",
            "hidden_size": 4096,
            # Missing num_hidden_layers
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))

        with pytest.raises(ValueError, match="num_hidden_layers"):
            load_model_metadata(str(tmp_path))

    def test_config_not_found(self, tmp_path: Path):
        """Test error when config.json doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_model_metadata(str(tmp_path))

    def test_params_override(self, tmp_config_dir: Path):
        """Test that params_b parameter overrides estimation."""
        metadata = load_model_metadata(str(tmp_config_dir), params_b=13.0)
        assert metadata.params_billions == 13.0


class TestEstimateParams:
    """Tests for parameter estimation."""

    def test_estimate_params_7b(self, llama_metadata: ModelMetadata):
        """Test parameter estimation for 7B-scale model."""
        estimated = estimate_params_from_config(llama_metadata)

        # Should be in the ballpark of 7B
        assert 5e9 < estimated < 10e9

    def test_estimate_params_with_intermediate(self, llama_8b_metadata: ModelMetadata):
        """Test parameter estimation with explicit intermediate size."""
        estimated = estimate_params_from_config(llama_8b_metadata)

        # Should be in the ballpark of 8B
        assert 6e9 < estimated < 12e9


class TestLookupKnownModels:
    """Tests for known model size lookup."""

    def test_lookup_llama_7b(self):
        """Test lookup for LLaMA 2 7B."""
        size = lookup_known_model_size("meta-llama/Llama-2-7b-hf")
        assert size == 7.0

    def test_lookup_llama_70b(self):
        """Test lookup for LLaMA 70B."""
        size = lookup_known_model_size("meta-llama/llama-2-70b-chat-hf")
        assert size == 70.0

    def test_lookup_mistral(self):
        """Test lookup for Mistral 7B."""
        size = lookup_known_model_size("mistralai/Mistral-7B-v0.1")
        assert size == 7.0

    def test_lookup_unknown(self):
        """Test lookup for unknown model."""
        size = lookup_known_model_size("some-random/unknown-model")
        assert size is None
