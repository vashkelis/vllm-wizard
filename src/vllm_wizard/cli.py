"""vLLM Wizard CLI - Configuration generator and GPU sizing tool."""

import json
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from vllm_wizard import __version__
from vllm_wizard.hardware.detect import detect_gpus
from vllm_wizard.planning.planner import run_plan
from vllm_wizard.render.commands import render_docker_compose, render_k8s_values
from vllm_wizard.render.profile import (
    load_profile,
    profile_to_request,
    request_to_profile,
    save_profile,
)
from vllm_wizard.render.report import render_console_report, render_gpu_list, render_json
from vllm_wizard.schemas.inputs import (
    BatchingMode,
    DType,
    HardwareInput,
    Interconnect,
    KVCacheDType,
    ModelInput,
    PlanRequest,
    PolicyInput,
    Quantization,
    WorkloadInput,
)

app = typer.Typer(
    name="vllm-wizard",
    help="vLLM Configuration Wizard - Generate optimal vLLM configurations and estimate VRAM usage.",
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"vllm-wizard version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """vLLM Configuration Wizard - Generate optimal vLLM configurations."""
    pass


@app.command()
def detect(
    json_output: Annotated[
        bool, typer.Option("--json", help="Output as JSON")
    ] = False,
) -> None:
    """Detect available GPUs on this system."""
    gpus = detect_gpus()

    if json_output:
        output = [gpu.model_dump() for gpu in gpus]
        console.print(json.dumps(output, indent=2))
    else:
        if gpus:
            render_gpu_list(gpus, console)
        else:
            console.print("[yellow]No NVIDIA GPUs detected.[/yellow]")
            console.print("Ensure nvidia-smi is installed and GPUs are available.")


@app.command()
def plan(
    # Model options
    model: Annotated[str, typer.Option("--model", "-m", help="HF model id or local path")],
    revision: Annotated[Optional[str], typer.Option("--revision", help="Model revision")] = None,
    trust_remote_code: Annotated[
        bool, typer.Option("--trust-remote-code", help="Trust remote code")
    ] = False,
    dtype: Annotated[
        DType, typer.Option("--dtype", help="Model weight dtype")
    ] = DType.AUTO,
    quantization: Annotated[
        Quantization, typer.Option("--quantization", "-q", help="Quantization method")
    ] = Quantization.NONE,
    kv_cache_dtype: Annotated[
        KVCacheDType, typer.Option("--kv-cache-dtype", help="KV cache dtype")
    ] = KVCacheDType.AUTO,
    max_model_len: Annotated[
        Optional[int], typer.Option("--max-model-len", help="Target context length")
    ] = None,
    params_b: Annotated[
        Optional[float], typer.Option("--params-b", help="Model parameters in billions")
    ] = None,
    # Hardware options
    gpu: Annotated[
        str, typer.Option("--gpu", help="GPU name or 'auto' for detection")
    ] = "auto",
    gpus: Annotated[int, typer.Option("--gpus", help="Number of GPUs")] = 1,
    vram_gb: Annotated[
        Optional[float], typer.Option("--vram-gb", help="VRAM per GPU in GB")
    ] = None,
    interconnect: Annotated[
        Interconnect, typer.Option("--interconnect", help="GPU interconnect type")
    ] = Interconnect.UNKNOWN,
    tensor_parallel_size: Annotated[
        Optional[int], typer.Option("--tensor-parallel-size", "--tp", help="Tensor parallel size")
    ] = None,
    # Workload options
    prompt_tokens: Annotated[
        int, typer.Option("--prompt-tokens", help="Typical prompt token count")
    ] = 512,
    gen_tokens: Annotated[
        int, typer.Option("--gen-tokens", help="Typical generation token count")
    ] = 256,
    concurrency: Annotated[
        int, typer.Option("--concurrency", "-c", help="Simultaneous sequences")
    ] = 1,
    batching_mode: Annotated[
        BatchingMode, typer.Option("--batching-mode", help="Batching optimization mode")
    ] = BatchingMode.BALANCED,
    # Policy options
    gpu_memory_utilization: Annotated[
        float, typer.Option("--gpu-memory-utilization", help="GPU memory utilization")
    ] = 0.90,
    overhead_gb: Annotated[
        Optional[float], typer.Option("--overhead-gb", help="Fixed overhead in GB")
    ] = None,
    fragmentation_factor: Annotated[
        float, typer.Option("--fragmentation-factor", help="KV cache fragmentation factor")
    ] = 1.15,
    headroom_gb: Annotated[
        float, typer.Option("--headroom-gb", help="Minimum headroom in GB")
    ] = 1.0,
    # Output options
    profile: Annotated[
        Optional[Path], typer.Option("--profile", "-p", help="Load settings from profile YAML")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    explain: Annotated[
        bool, typer.Option("--explain", help="Include parameter explanations")
    ] = False,
) -> None:
    """Plan vLLM configuration and estimate VRAM usage."""
    try:
        # Load from profile or build request
        if profile:
            loaded_profile = load_profile(profile)
            request = profile_to_request(loaded_profile)
            request.explain = explain
        else:
            request = PlanRequest(
                model=ModelInput(
                    model=model,
                    revision=revision,
                    trust_remote_code=trust_remote_code,
                    dtype=dtype,
                    quantization=quantization,
                    kv_cache_dtype=kv_cache_dtype,
                    max_model_len=max_model_len,
                    params_b=params_b,
                ),
                hardware=HardwareInput(
                    gpu=gpu,
                    gpus=gpus,
                    vram_gb=vram_gb,
                    interconnect=interconnect,
                    tensor_parallel_size=tensor_parallel_size,
                ),
                workload=WorkloadInput(
                    prompt_tokens=prompt_tokens,
                    gen_tokens=gen_tokens,
                    concurrency=concurrency,
                    batching_mode=batching_mode,
                ),
                policy=PolicyInput(
                    gpu_memory_utilization=gpu_memory_utilization,
                    overhead_gb=overhead_gb,
                    fragmentation_factor=fragmentation_factor,
                    headroom_gb=headroom_gb,
                ),
                explain=explain,
            )

        # Run planning
        response = run_plan(request)

        # Output
        if json_output:
            console.print(render_json(response))
        else:
            render_console_report(response, console)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def generate(
    # Output options (required)
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Output directory for artifacts")
    ],
    # Model options
    model: Annotated[str, typer.Option("--model", "-m", help="HF model id or local path")],
    revision: Annotated[Optional[str], typer.Option("--revision", help="Model revision")] = None,
    trust_remote_code: Annotated[
        bool, typer.Option("--trust-remote-code", help="Trust remote code")
    ] = False,
    dtype: Annotated[DType, typer.Option("--dtype", help="Model weight dtype")] = DType.AUTO,
    quantization: Annotated[
        Quantization, typer.Option("--quantization", "-q", help="Quantization method")
    ] = Quantization.NONE,
    kv_cache_dtype: Annotated[
        KVCacheDType, typer.Option("--kv-cache-dtype", help="KV cache dtype")
    ] = KVCacheDType.AUTO,
    max_model_len: Annotated[
        Optional[int], typer.Option("--max-model-len", help="Target context length")
    ] = None,
    params_b: Annotated[
        Optional[float], typer.Option("--params-b", help="Model parameters in billions")
    ] = None,
    # Hardware options
    gpu: Annotated[str, typer.Option("--gpu", help="GPU name or 'auto'")] = "auto",
    gpus: Annotated[int, typer.Option("--gpus", help="Number of GPUs")] = 1,
    vram_gb: Annotated[Optional[float], typer.Option("--vram-gb", help="VRAM per GPU")] = None,
    interconnect: Annotated[
        Interconnect, typer.Option("--interconnect", help="GPU interconnect")
    ] = Interconnect.UNKNOWN,
    tensor_parallel_size: Annotated[
        Optional[int], typer.Option("--tensor-parallel-size", "--tp", help="TP size")
    ] = None,
    # Workload options
    prompt_tokens: Annotated[int, typer.Option("--prompt-tokens", help="Prompt tokens")] = 512,
    gen_tokens: Annotated[int, typer.Option("--gen-tokens", help="Generation tokens")] = 256,
    concurrency: Annotated[int, typer.Option("--concurrency", "-c", help="Concurrency")] = 1,
    batching_mode: Annotated[
        BatchingMode, typer.Option("--batching-mode", help="Batching mode")
    ] = BatchingMode.BALANCED,
    # Policy options
    gpu_memory_utilization: Annotated[
        float, typer.Option("--gpu-memory-utilization", help="GPU memory utilization")
    ] = 0.90,
    overhead_gb: Annotated[Optional[float], typer.Option("--overhead-gb", help="Overhead GB")] = None,
    fragmentation_factor: Annotated[
        float, typer.Option("--fragmentation-factor", help="Fragmentation factor")
    ] = 1.15,
    headroom_gb: Annotated[float, typer.Option("--headroom-gb", help="Headroom GB")] = 1.0,
    # Output options
    emit: Annotated[
        str, typer.Option("--emit", help="Artifacts to emit (comma-separated: command,profile,compose,k8s)")
    ] = "command,profile",
    profile: Annotated[
        Optional[Path], typer.Option("--profile", "-p", help="Load settings from profile YAML")
    ] = None,
) -> None:
    """Generate vLLM configuration artifacts."""
    try:
        # Parse emit options
        emit_list = [e.strip() for e in emit.split(",")]

        # Load from profile or build request
        if profile:
            loaded_profile = load_profile(profile)
            request = profile_to_request(loaded_profile)
        else:
            request = PlanRequest(
                model=ModelInput(
                    model=model,
                    revision=revision,
                    trust_remote_code=trust_remote_code,
                    dtype=dtype,
                    quantization=quantization,
                    kv_cache_dtype=kv_cache_dtype,
                    max_model_len=max_model_len,
                    params_b=params_b,
                ),
                hardware=HardwareInput(
                    gpu=gpu,
                    gpus=gpus,
                    vram_gb=vram_gb,
                    interconnect=interconnect,
                    tensor_parallel_size=tensor_parallel_size,
                ),
                workload=WorkloadInput(
                    prompt_tokens=prompt_tokens,
                    gen_tokens=gen_tokens,
                    concurrency=concurrency,
                    batching_mode=batching_mode,
                ),
                policy=PolicyInput(
                    gpu_memory_utilization=gpu_memory_utilization,
                    overhead_gb=overhead_gb,
                    fragmentation_factor=fragmentation_factor,
                    headroom_gb=headroom_gb,
                ),
            )

        # Run planning
        response = run_plan(request)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        generated_files: list[str] = []

        # Generate artifacts
        if "command" in emit_list:
            cmd_path = output_dir / "serve_command.sh"
            cmd_path.write_text(f"#!/bin/bash\n\n{response.artifacts.serve_command}\n")
            generated_files.append(str(cmd_path))

        if "profile" in emit_list:
            profile_path = output_dir / "profile.yaml"
            profile_obj = request_to_profile(request, emit_list)
            save_profile(profile_obj, profile_path)
            generated_files.append(str(profile_path))

        if "compose" in emit_list:
            compose_path = output_dir / "docker-compose.yaml"
            compose_path.write_text(response.artifacts.docker_compose or "")
            generated_files.append(str(compose_path))

        if "k8s" in emit_list:
            k8s_path = output_dir / "k8s-values.yaml"
            k8s_content = render_k8s_values(response.config)
            k8s_path.write_text(k8s_content)
            generated_files.append(str(k8s_path))

        # Also save JSON response
        json_path = output_dir / "plan.json"
        json_path.write_text(render_json(response))
        generated_files.append(str(json_path))

        # Print summary
        console.print()
        console.print("[green]Generated artifacts:[/green]")
        for f in generated_files:
            console.print(f"  - {f}")
        console.print()

        if response.feasibility.fits:
            console.print("[green]Configuration fits in VRAM.[/green]")
        else:
            console.print("[red]Warning: Configuration may not fit in VRAM.[/red]")
            for warning in response.feasibility.warnings:
                console.print(f"  [yellow]! {warning}[/yellow]")

        console.print()
        console.print("[bold]Next steps:[/bold]")
        console.print(f"  1. Review generated files in {output_dir}")
        console.print("  2. Run the serve command or use docker-compose up")
        console.print("  3. Test with a sample request before production use")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
