"""Console report rendering with Rich."""

import json
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from vllm_wizard.schemas.outputs import GPUInfo, OOMRisk, PlanResponse


def render_console_report(response: PlanResponse, console: Optional[Console] = None) -> None:
    """Render a rich console report of the plan response.

    Args:
        response: Plan response to render
        console: Optional console instance
    """
    if console is None:
        console = Console()

    # Header
    _render_header(console, response)

    # Feasibility section
    _render_feasibility(console, response)

    # VRAM breakdown table
    _render_vram_table(console, response)

    # Recommendations
    _render_recommendations(console, response)

    # Performance estimates
    _render_performance(console, response)

    # Serve command
    _render_command(console, response)

    # Warnings
    _render_warnings(console, response)


def _render_header(console: Console, response: PlanResponse) -> None:
    """Render report header."""
    fits = response.feasibility.fits
    status = "[green]FITS[/green]" if fits else "[red]DOES NOT FIT[/red]"

    console.print()
    console.print(Panel(f"vLLM Configuration Report - {status}", style="bold"))
    console.print()


def _render_feasibility(console: Console, response: PlanResponse) -> None:
    """Render feasibility summary."""
    f = response.feasibility

    risk_colors = {
        OOMRisk.LOW: "green",
        OOMRisk.MEDIUM: "yellow",
        OOMRisk.HIGH: "red",
    }
    risk_color = risk_colors.get(f.oom_risk, "white")

    console.print("[bold]Feasibility Summary[/bold]")
    console.print(f"  Status: {'[green]Fits[/green]' if f.fits else '[red]Does not fit[/red]'}")
    console.print(f"  OOM Risk: [{risk_color}]{f.oom_risk.value.upper()}[/{risk_color}]")
    console.print(f"  Available Headroom: {f.headroom_gb:.2f} GiB")
    console.print()


def _render_vram_table(console: Console, response: PlanResponse) -> None:
    """Render VRAM breakdown table."""
    f = response.feasibility

    table = Table(title="VRAM Breakdown", show_header=True, header_style="bold")
    table.add_column("Component", style="cyan")
    table.add_column("Size (GiB)", justify="right")
    table.add_column("% of Allocatable", justify="right")

    allocatable = f.vram_target_alloc_gb

    def pct(val: float) -> str:
        if allocatable > 0:
            return f"{(val / allocatable) * 100:.1f}%"
        return "-"

    table.add_row("Total VRAM", f"{f.vram_total_gb:.2f}", "-")
    table.add_row(
        "Target Allocation",
        f"{f.vram_target_alloc_gb:.2f}",
        f"{(f.vram_target_alloc_gb / f.vram_total_gb) * 100:.0f}%",
    )
    table.add_row("", "", "")
    table.add_row("Model Weights", f"{f.weights_gb:.2f}", pct(f.weights_gb))
    table.add_row("KV Cache", f"{f.kv_cache_gb:.2f}", pct(f.kv_cache_gb))
    table.add_row("Overhead", f"{f.overhead_gb:.2f}", pct(f.overhead_gb))
    table.add_row("", "", "")
    table.add_row(
        "[bold]Headroom[/bold]",
        f"[bold]{f.headroom_gb:.2f}[/bold]",
        pct(f.headroom_gb),
    )

    console.print(table)
    console.print()

    # Max calculations
    console.print(f"  Max concurrency at target context: {f.max_concurrency_at_context}")
    console.print(f"  Max context at target concurrency: {f.max_context_at_concurrency:,}")
    console.print()


def _render_recommendations(console: Console, response: PlanResponse) -> None:
    """Render recommended configuration."""
    config = response.config

    table = Table(title="Recommended vLLM Configuration", show_header=True, header_style="bold")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value")
    table.add_column("Explanation", style="dim")

    explanations = config.explanations

    table.add_row(
        "model", config.model, explanations.get("model", "")
    )
    table.add_row(
        "tensor_parallel_size",
        str(config.tensor_parallel_size),
        explanations.get("tensor_parallel_size", ""),
    )
    table.add_row("dtype", config.dtype, explanations.get("dtype", ""))
    table.add_row(
        "gpu_memory_utilization",
        str(config.gpu_memory_utilization),
        explanations.get("gpu_memory_utilization", ""),
    )
    table.add_row(
        "max_model_len",
        f"{config.max_model_len:,}",
        explanations.get("max_model_len", ""),
    )

    if config.kv_cache_dtype:
        table.add_row(
            "kv_cache_dtype",
            config.kv_cache_dtype,
            explanations.get("kv_cache_dtype", ""),
        )

    if config.quantization:
        table.add_row(
            "quantization",
            config.quantization,
            explanations.get("quantization", ""),
        )

    if config.max_num_seqs:
        table.add_row(
            "max_num_seqs",
            str(config.max_num_seqs),
            explanations.get("max_num_seqs", ""),
        )

    if config.max_num_batched_tokens:
        table.add_row(
            "max_num_batched_tokens",
            f"{config.max_num_batched_tokens:,}",
            explanations.get("max_num_batched_tokens", ""),
        )

    console.print(table)
    console.print()


def _render_performance(console: Console, response: PlanResponse) -> None:
    """Render performance estimates."""
    perf = response.performance

    console.print("[bold]Performance Estimates[/bold] [dim](approximate)[/dim]")
    console.print(
        f"  Decode: {perf.decode_toks_per_s_range[0]:.0f} - "
        f"{perf.decode_toks_per_s_range[1]:.0f} tokens/s"
    )

    if perf.prefill_toks_per_s_range:
        console.print(
            f"  Prefill: {perf.prefill_toks_per_s_range[0]:.0f} - "
            f"{perf.prefill_toks_per_s_range[1]:.0f} tokens/s"
        )

    if perf.ttft_ms_range:
        console.print(
            f"  TTFT: {perf.ttft_ms_range[0]:.0f} - {perf.ttft_ms_range[1]:.0f} ms"
        )

    console.print()
    console.print("[dim]Assumptions:[/dim]")
    for assumption in perf.assumptions[:3]:  # Show first 3
        console.print(f"  [dim]- {assumption}[/dim]")
    console.print()


def _render_command(console: Console, response: PlanResponse) -> None:
    """Render the serve command."""
    console.print("[bold]Recommended Command[/bold]")
    console.print()
    console.print(Panel(response.artifacts.serve_command, title="vllm serve", border_style="green"))
    console.print()


def _render_warnings(console: Console, response: PlanResponse) -> None:
    """Render warnings."""
    warnings = response.feasibility.warnings

    if not warnings:
        return

    console.print("[bold yellow]Warnings[/bold yellow]")
    for warning in warnings:
        console.print(f"  [yellow]! {warning}[/yellow]")
    console.print()


def render_json(response: PlanResponse, indent: int = 2) -> str:
    """Render response as JSON.

    Args:
        response: Plan response
        indent: JSON indentation

    Returns:
        JSON string
    """
    return response.model_dump_json(indent=indent)


def render_gpu_list(gpus: list[GPUInfo], console: Optional[Console] = None) -> None:
    """Render detected GPU list.

    Args:
        gpus: List of detected GPUs
        console: Optional console instance
    """
    if console is None:
        console = Console()

    if not gpus:
        console.print("[yellow]No GPUs detected[/yellow]")
        return

    table = Table(title="Detected GPUs", show_header=True, header_style="bold")
    table.add_column("#", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("VRAM (GiB)", justify="right")
    table.add_column("Driver", justify="center")
    table.add_column("CUDA", justify="center")

    for i, gpu in enumerate(gpus):
        table.add_row(
            str(i),
            gpu.name,
            f"{gpu.vram_gib:.1f}",
            gpu.driver_version or "-",
            gpu.cuda_version or "-",
        )

    console.print(table)
