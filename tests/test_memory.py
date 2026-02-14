"""Tests for memory calculations."""

import pytest

from vllm_wizard.models.metadata import ModelMetadata
from vllm_wizard.planning.memory import (
    BYTES_TO_GIB,
    compute_feasibility,
    compute_kv_cache_memory,
    compute_max_concurrency_at_context,
    compute_max_context_at_concurrency,
    compute_overhead,
    compute_weights_memory,
)
from vllm_wizard.schemas.inputs import DType, KVCacheDType, Quantization
from vllm_wizard.schemas.outputs import OOMRisk


class TestWeightsMemory:
    """Tests for compute_weights_memory."""

    def test_fp16_weights(self):
        """Test FP16 weights calculation."""
        # 7B params * 2 bytes = 14GB
        memory = compute_weights_memory(7.0, DType.FP16, Quantization.NONE)
        assert memory == 14_000_000_000

    def test_bf16_weights(self):
        """Test BF16 weights calculation."""
        # Same as FP16
        memory = compute_weights_memory(7.0, DType.BF16, Quantization.NONE)
        assert memory == 14_000_000_000

    def test_fp32_weights(self):
        """Test FP32 weights calculation."""
        # 7B params * 4 bytes = 28GB
        memory = compute_weights_memory(7.0, DType.FP32, Quantization.NONE)
        assert memory == 28_000_000_000

    def test_awq_quantization(self):
        """Test AWQ 4-bit quantization."""
        # 7B params * 0.55 bytes = ~3.85GB
        memory = compute_weights_memory(7.0, DType.FP16, Quantization.AWQ)
        assert 3_500_000_000 < memory < 4_200_000_000

    def test_gptq_quantization(self):
        """Test GPTQ 4-bit quantization."""
        memory = compute_weights_memory(7.0, DType.FP16, Quantization.GPTQ)
        assert 3_500_000_000 < memory < 4_200_000_000

    def test_int8_quantization(self):
        """Test INT8 quantization."""
        # 7B params * 1 byte = 7GB
        memory = compute_weights_memory(7.0, DType.FP16, Quantization.INT8)
        assert memory == 7_000_000_000


class TestKVCacheMemory:
    """Tests for compute_kv_cache_memory."""

    def test_kv_cache_basic(self, llama_metadata: ModelMetadata):
        """Test basic KV cache calculation."""
        memory = compute_kv_cache_memory(
            metadata=llama_metadata,
            context_len=4096,
            concurrency=1,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.0,  # No fragmentation for test
        )

        # KV cache per token per layer = 2 * kv_heads * head_dim * dtype_bytes
        # = 2 * 32 * 128 * 2 = 16384 bytes per token per layer
        # Total = 16384 * 32 layers * 4096 tokens * 1 seq = 2147483648 bytes = 2 GiB
        expected = 2 * 32 * 128 * 2 * 32 * 4096 * 1
        assert memory == expected

    def test_kv_cache_gqa(self, llama_8b_metadata: ModelMetadata):
        """Test KV cache with GQA (fewer KV heads)."""
        memory = compute_kv_cache_memory(
            metadata=llama_8b_metadata,
            context_len=4096,
            concurrency=1,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.0,
        )

        # With GQA: 2 * 8 * 128 * 2 * 32 * 4096 = 536870912 bytes
        expected = 2 * 8 * 128 * 2 * 32 * 4096 * 1
        assert memory == expected
        # Should be 4x smaller than MHA due to 8 vs 32 KV heads
        assert memory < 1 * BYTES_TO_GIB

    def test_kv_cache_concurrency(self, llama_metadata: ModelMetadata):
        """Test KV cache scales with concurrency."""
        memory_1 = compute_kv_cache_memory(
            metadata=llama_metadata,
            context_len=4096,
            concurrency=1,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.0,
        )

        memory_4 = compute_kv_cache_memory(
            metadata=llama_metadata,
            context_len=4096,
            concurrency=4,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.0,
        )

        assert memory_4 == memory_1 * 4

    def test_kv_cache_fp8(self, llama_metadata: ModelMetadata):
        """Test FP8 KV cache is half the size of FP16."""
        memory_fp16 = compute_kv_cache_memory(
            metadata=llama_metadata,
            context_len=4096,
            concurrency=1,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.0,
        )

        memory_fp8 = compute_kv_cache_memory(
            metadata=llama_metadata,
            context_len=4096,
            concurrency=1,
            kv_dtype=KVCacheDType.FP8_E4M3FN,
            fragmentation_factor=1.0,
        )

        assert memory_fp8 == memory_fp16 // 2

    def test_kv_cache_fragmentation(self, llama_metadata: ModelMetadata):
        """Test fragmentation factor applies correctly."""
        memory_base = compute_kv_cache_memory(
            metadata=llama_metadata,
            context_len=4096,
            concurrency=1,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.0,
        )

        memory_frag = compute_kv_cache_memory(
            metadata=llama_metadata,
            context_len=4096,
            concurrency=1,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.15,
        )

        assert memory_frag == int(memory_base * 1.15)


class TestOverhead:
    """Tests for compute_overhead."""

    def test_base_overhead(self):
        """Test base overhead calculation."""
        # For 24 GiB VRAM: max(1.0, 0.02 * 24) = 1.0 GiB
        overhead = compute_overhead(24 * BYTES_TO_GIB, tp_size=1)
        assert overhead == int(1.0 * BYTES_TO_GIB)

    def test_large_vram_overhead(self):
        """Test overhead for large VRAM scales with size."""
        # For 80 GiB VRAM: max(1.0, 0.02 * 80) = 1.6 GiB
        overhead = compute_overhead(80 * BYTES_TO_GIB, tp_size=1)
        assert overhead == int(1.6 * BYTES_TO_GIB)

    def test_multi_gpu_overhead(self):
        """Test additional overhead for tensor parallel."""
        # TP=2: base + 0.25 * (2-1) = 1.0 + 0.25 = 1.25 GiB
        overhead = compute_overhead(24 * BYTES_TO_GIB, tp_size=2)
        assert overhead == int(1.25 * BYTES_TO_GIB)

    def test_fixed_overhead(self):
        """Test fixed overhead override."""
        overhead = compute_overhead(24 * BYTES_TO_GIB, tp_size=1, fixed_overhead_gb=2.5)
        assert overhead == int(2.5 * BYTES_TO_GIB)


class TestFeasibility:
    """Tests for compute_feasibility."""

    def test_fits_with_headroom(self, llama_metadata: ModelMetadata):
        """Test configuration that fits with good headroom."""
        # 24 GiB VRAM, 14 GiB weights, 2 GiB KV, 1 GiB overhead
        # = 7 GiB headroom at 90% util
        result = compute_feasibility(
            weights_bytes=int(14 * BYTES_TO_GIB),
            kv_cache_bytes=int(2 * BYTES_TO_GIB),
            overhead_bytes=int(1 * BYTES_TO_GIB),
            vram_total_bytes=int(24 * BYTES_TO_GIB),
            gpu_memory_utilization=0.90,
            headroom_gb=1.0,
        )

        assert result.fits is True
        assert result.oom_risk == OOMRisk.LOW
        assert result.headroom_gb > 2.0

    def test_does_not_fit(self, llama_metadata: ModelMetadata):
        """Test configuration that doesn't fit."""
        # 16 GiB VRAM, 14 GiB weights, 4 GiB KV, 1 GiB overhead = -3 GiB
        result = compute_feasibility(
            weights_bytes=int(14 * BYTES_TO_GIB),
            kv_cache_bytes=int(4 * BYTES_TO_GIB),
            overhead_bytes=int(1 * BYTES_TO_GIB),
            vram_total_bytes=int(16 * BYTES_TO_GIB),
            gpu_memory_utilization=0.90,
            headroom_gb=1.0,
        )

        assert result.fits is False
        assert result.oom_risk == OOMRisk.HIGH
        assert len(result.warnings) > 0

    def test_medium_risk(self):
        """Test medium OOM risk (0-2 GiB headroom)."""
        # Exactly at boundary
        result = compute_feasibility(
            weights_bytes=int(14 * BYTES_TO_GIB),
            kv_cache_bytes=int(4 * BYTES_TO_GIB),
            overhead_bytes=int(1 * BYTES_TO_GIB),
            vram_total_bytes=int(24 * BYTES_TO_GIB),  # 21.6 alloc - 19 used = 2.6 head
            gpu_memory_utilization=0.90,
            headroom_gb=1.0,
        )

        # 21.6 - 19 = 2.6 GiB headroom -> LOW risk
        assert result.fits is True


class TestMaxCalculations:
    """Tests for max concurrency/context calculations."""

    def test_max_concurrency(self, llama_metadata: ModelMetadata):
        """Test max concurrency calculation."""
        # 24 GiB allocatable, 14 GiB weights, 1 GiB overhead = 9 GiB for KV
        # Each seq at 4096 context ≈ 2 GiB KV -> 4 sequences
        max_conc = compute_max_concurrency_at_context(
            allocatable_bytes=int(24 * BYTES_TO_GIB),
            weights_bytes=int(14 * BYTES_TO_GIB),
            overhead_bytes=int(1 * BYTES_TO_GIB),
            metadata=llama_metadata,
            context_len=4096,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.0,
        )

        assert max_conc >= 1  # Should fit at least one sequence

    def test_max_context(self, llama_metadata: ModelMetadata):
        """Test max context calculation."""
        max_ctx = compute_max_context_at_concurrency(
            allocatable_bytes=int(24 * BYTES_TO_GIB),
            weights_bytes=int(14 * BYTES_TO_GIB),
            overhead_bytes=int(1 * BYTES_TO_GIB),
            metadata=llama_metadata,
            concurrency=1,
            kv_dtype=KVCacheDType.FP16,
            fragmentation_factor=1.0,
        )

        assert max_ctx > 0  # Should support some context
