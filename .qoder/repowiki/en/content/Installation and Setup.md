# Installation and Setup

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [pyproject.toml](file://pyproject.toml)
- [requirements.txt](file://requirements.txt)
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py)
- [src/vllm_wizard/hardware/detect.py](file://src/vllm_wizard/hardware/detect.py)
- [src/vllm_wizard/planning/planner.py](file://src/vllm_wizard/planning/planner.py)
- [src/vllm_wizard/schemas/inputs.py](file://src/vllm_wizard/schemas/inputs.py)
- [src/vllm_wizard/schemas/outputs.py](file://src/vllm_wizard/schemas/outputs.py)
- [tests/test_cli.py](file://tests/test_cli.py)
- [examples/profiles/sample.yaml](file://examples/profiles/sample.yaml)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation Methods](#installation-methods)
4. [Platform-Specific Setup](#platform-specific-setup)
5. [Base vs Development/Web UI Installations](#base-vs-developmentweb-ui-installations)
6. [Verification Steps](#verification-steps)
7. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
8. [Dependency Conflicts and Compatibility](#dependency-conflicts-and-compatibility)
9. [Initial Configuration Recommendations](#initial-configuration-recommendations)
10. [Architecture Overview](#architecture-overview)
11. [Conclusion](#conclusion)

## Introduction
This guide provides comprehensive installation and setup instructions for the vLLM Config Wizard. It covers all installation methods (pip from source, development dependencies, and optional web UI support), prerequisites, platform-specific setup, verification steps, troubleshooting, and best practices for environment configuration.

## Prerequisites
Before installing vLLM Config Wizard, ensure your system meets the following requirements:

- Python 3.9 or newer
- A compatible operating system:
  - Linux (first-class support)
  - macOS (best-effort; CLI works; GPU detection may vary)
  - Windows (best-effort; CLI works; GPU detection may vary)
- NVIDIA GPU with NVIDIA drivers and CUDA toolkit installed
- Access to nvidia-smi for GPU detection

Notes:
- The tool relies on nvidia-smi for GPU detection. On systems without nvidia-smi, you must provide GPU specifications manually (e.g., GPU name and VRAM).
- The project targets Python 3.9+ as defined in the project metadata.

**Section sources**
- [pyproject.toml](file://pyproject.toml#L11-L27)
- [requirements.txt](file://requirements.txt#L42-L47)
- [src/vllm_wizard/hardware/detect.py](file://src/vllm_wizard/hardware/detect.py#L10-L72)

## Installation Methods
Install vLLM Config Wizard using pip from the repository root. Choose the installation variant that matches your needs.

- Base installation (minimal dependencies)
  - Installs core dependencies required to run the CLI and perform GPU detection and planning.
  - Command: pip install -e .

- Development installation
  - Adds testing and linting tools for contributors.
  - Command: pip install -e ".[dev]"

- Web UI installation (optional)
  - Adds FastAPI, Uvicorn, and Jinja2 for the optional web interface.
  - Command: pip install -e ".[web]"

- Combined installation
  - Install both development and web UI dependencies in a single command.
  - Command: pip install -e ".[dev,web]"

Notes:
- The project defines optional extras for development and web UI support in the packaging configuration.
- The CLI entry point is configured to run the main application.

**Section sources**
- [README.md](file://README.md#L13-L24)
- [pyproject.toml](file://pyproject.toml#L37-L47)
- [pyproject.toml](file://pyproject.toml#L49-L50)

## Platform-Specific Setup
Follow platform-specific guidance below to prepare your environment for vLLM Config Wizard.

- Linux
  - Ensure NVIDIA drivers and CUDA toolkit are installed.
  - Verify nvidia-smi is available in PATH for automatic GPU detection.
  - Install Python 3.9+ and pip.
  - Use the base installation command to install the package in editable mode.

- macOS
  - Install Python 3.9+ and pip.
  - GPU detection may vary; if nvidia-smi is unavailable, provide GPU details manually (GPU name and VRAM).
  - Use the base installation command.

- Windows
  - Install Python 3.9+ and pip.
  - GPU detection may vary; if nvidia-smi is unavailable, provide GPU details manually.
  - Use the base installation command.

Notes:
- The project documentation indicates Linux as first-class, with macOS and Windows as best-effort for the CLI.

**Section sources**
- [requirements.txt](file://requirements.txt#L42-L47)
- [README.md](file://README.md#L278-L292)

## Base vs Development/Web UI Installations
Understanding the differences between installation variants helps you choose the right setup for your use case.

- Base installation
  - Core dependencies only:
    - pydantic
    - typer
    - rich
    - pyyaml
    - huggingface_hub
  - Suitable for running the CLI and performing planning without development or web UI features.

- Development installation
  - Adds testing and linting tools:
    - pytest
    - pytest-cov
    - ruff
  - Ideal for contributors who need to run tests and lint code.

- Web UI installation
  - Adds web framework dependencies:
    - fastapi
    - uvicorn
    - jinja2
  - Enables the optional web interface (if implemented). The CLI entry point remains unchanged.

- Combined installation
  - Installs both development and web UI dependencies in one step.

**Section sources**
- [pyproject.toml](file://pyproject.toml#L29-L35)
- [pyproject.toml](file://pyproject.toml#L37-L47)
- [README.md](file://README.md#L278-L292)

## Verification Steps
After installation, verify that vLLM Config Wizard is working correctly.

- Check CLI availability
  - Run the CLI entry point to confirm installation.
  - Example: vllm-wizard --version

- Detect GPUs
  - Run the detect command to verify GPU detection.
  - Example: vllm-wizard detect
  - If nvidia-smi is not available, the tool will print a message indicating that GPU detection requires nvidia-smi.

- Run a basic plan
  - Use a minimal plan command to ensure the tool can process inputs and produce output.
  - Example: vllm-wizard plan --model <your-model-id-or-path> --json

- Generate artifacts
  - Use the generate command to create configuration files.
  - Example: vllm-wizard generate --output-dir ./vllm-config --model <your-model-id-or-path> --emit command,profile

Notes:
- The tests demonstrate expected behavior for the CLI commands, including JSON output and artifact generation.

**Section sources**
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py#L44-L58)
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py#L62-L80)
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py#L215-L381)
- [tests/test_cli.py](file://tests/test_cli.py#L184-L192)
- [tests/test_cli.py](file://tests/test_cli.py#L19-L50)
- [tests/test_cli.py](file://tests/test_cli.py#L52-L133)
- [tests/test_cli.py](file://tests/test_cli.py#L135-L182)

## Common Issues and Troubleshooting
Encounter one of these common issues during installation or operation?

- No NVIDIA GPUs detected
  - Symptom: The detect command reports no GPUs or prints a message indicating that nvidia-smi is required.
  - Resolution: Ensure nvidia-smi is installed and available in PATH. Alternatively, provide GPU details manually using CLI flags (GPU name and VRAM).

- Missing optional web UI dependencies
  - Symptom: Attempting to use web UI features without installing the web extra.
  - Resolution: Install the web UI extra: pip install -e ".[web]" or the combined dev+web extra.

- Development tooling not available
  - Symptom: Running tests or linting fails because pytest/ruff are not installed.
  - Resolution: Install the dev extra: pip install -e ".[dev]" or the combined dev+web extra.

- Python version mismatch
  - Symptom: Installation fails due to unsupported Python version.
  - Resolution: Use Python 3.9 or newer as required by the project.

- Permission errors during installation
  - Symptom: Installation fails due to permissions.
  - Resolution: Use virtual environments or install with elevated privileges if necessary.

- Model metadata errors
  - Symptom: Errors when loading model metadata due to missing fields.
  - Resolution: Provide model parameters explicitly or ensure the model configuration contains required fields. The tool may require explicit parameter counts for unknown models.

**Section sources**
- [src/vllm_wizard/hardware/detect.py](file://src/vllm_wizard/hardware/detect.py#L10-L72)
- [src/vllm_wizard/planning/planner.py](file://src/vllm_wizard/planning/planner.py#L41-L45)
- [pyproject.toml](file://pyproject.toml#L11-L27)
- [requirements.txt](file://requirements.txt#L486-L493)

## Dependency Conflicts and Compatibility
Manage dependencies and avoid conflicts by following these guidelines.

- Core dependencies
  - pydantic: Used for input/output schemas and validation.
  - typer: CLI framework for command-line interface.
  - rich: Rich text rendering for console output.
  - pyyaml: YAML serialization for profiles.
  - huggingface_hub: Optional model metadata fetching from Hugging Face.

- Optional dependencies
  - fastapi, uvicorn, jinja2: Required for the optional web UI.
  - pytest, pytest-cov, ruff: Required for development/testing.

- Version compatibility
  - Python: Requires Python 3.9+.
  - The project specifies supported Python versions in classifiers and requires-python metadata.

- Conflict prevention
  - Use virtual environments to isolate dependencies.
  - Prefer installing optional extras separately to avoid unnecessary dependencies.
  - Pin versions when necessary to ensure reproducibility.

**Section sources**
- [pyproject.toml](file://pyproject.toml#L29-L35)
- [pyproject.toml](file://pyproject.toml#L37-L47)
- [pyproject.toml](file://pyproject.toml#L11-L27)

## Initial Configuration Recommendations
Set up your environment and initial configuration for optimal results.

- Environment setup
  - Use a virtual environment to manage dependencies.
  - Ensure nvidia-smi is available for automatic GPU detection.
  - Keep Python updated to 3.9+.

- First-time usage
  - Run the detect command to verify GPU detection.
  - If detection fails, provide GPU details manually using CLI flags.
  - Start with a simple plan command and review the feasibility report.
  - Use the generate command to create artifacts for quick deployment.

- Profile-based workflow
  - Save frequently used configurations as YAML profiles.
  - Load profiles with the plan and generate commands to reproduce configurations.

- Best practices
  - Always validate VRAM feasibility before deploying.
  - Adjust memory utilization and fragmentation factors based on your workload.
  - Use JSON output for scripting and automation.

**Section sources**
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py#L62-L80)
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py#L82-L213)
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py#L215-L381)
- [examples/profiles/sample.yaml](file://examples/profiles/sample.yaml#L1-L40)

## Architecture Overview
The installation and runtime architecture consists of the CLI entry point, core planning modules, hardware detection, and optional web UI components.

```mermaid
graph TB
subgraph "CLI"
CLI["vllm-wizard CLI<br/>Typer-based commands"]
end
subgraph "Core Modules"
Planner["planner.py<br/>run_plan orchestration"]
Detect["detect.py<br/>GPU detection via nvidia-smi"]
Schemas["schemas/<br/>Pydantic models"]
end
subgraph "Optional Web UI"
FastAPI["FastAPI app"]
Uvicorn["Uvicorn ASGI server"]
Jinja2["Jinja2 templates"]
end
subgraph "External Tools"
NSMI["nvidia-smi"]
HFHub["huggingface_hub"]
end
CLI --> Planner
Planner --> Detect
Planner --> Schemas
CLI --> Schemas
FastAPI --> Uvicorn
FastAPI --> Jinja2
Detect --> NSMI
Planner --> HFHub
```

**Diagram sources**
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py#L35-L39)
- [src/vllm_wizard/planning/planner.py](file://src/vllm_wizard/planning/planner.py#L21-L136)
- [src/vllm_wizard/hardware/detect.py](file://src/vllm_wizard/hardware/detect.py#L10-L72)
- [src/vllm_wizard/schemas/inputs.py](file://src/vllm_wizard/schemas/inputs.py#L54-L110)
- [src/vllm_wizard/schemas/outputs.py](file://src/vllm_wizard/schemas/outputs.py#L17-L118)
- [pyproject.toml](file://pyproject.toml#L43-L47)

## Conclusion
You now have the information needed to install and set up vLLM Config Wizard across platforms, choose the appropriate installation variant, and troubleshoot common issues. Use the verification steps to confirm a successful installation and follow the initial configuration recommendations for reliable operation. For development or web UI features, install the respective optional extras and adhere to the dependency compatibility guidelines.