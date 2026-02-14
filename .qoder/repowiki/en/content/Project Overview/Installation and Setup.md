# Installation and Setup

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [pyproject.toml](file://pyproject.toml)
- [requirements.txt](file://requirements.txt)
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py)
- [src/vllm_wizard/hardware/detect.py](file://src/vllm_wizard/hardware/detect.py)
- [src/vllm_wizard/planning/planner.py](file://src/vllm_wizard/planning/planner.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation Methods](#installation-methods)
4. [Platform-Specific Guidance](#platform-specific-guidance)
5. [Environment Setup](#environment-setup)
6. [Verification and First Run](#verification-and-first-run)
7. [Dependency Management](#dependency-management)
8. [Troubleshooting Common Issues](#troubleshooting-common-issues)
9. [Conclusion](#conclusion)

## Introduction
This guide provides comprehensive installation and setup instructions for the vLLM Config Wizard. It covers all installation methods (pip install from source), development dependencies, optional web UI support, prerequisites, environment setup, verification steps, platform-specific guidance, and troubleshooting.

## Prerequisites
Before installing vLLM Config Wizard, ensure your system meets the following requirements:

- Python 3.9 or newer
- NVIDIA GPU with NVIDIA drivers installed
- nvidia-smi available on PATH (required for automatic GPU detection)
- Access to either:
  - Local Hugging Face model files, or
  - Internet connectivity to fetch model metadata from Hugging Face Hub

Notes:
- Automatic GPU detection relies on nvidia-smi. On macOS and Windows, GPU detection may not work; you can still run the tool by manually specifying hardware parameters.
- The tool uses Hugging Face Hub for model metadata when models are provided by ID. If offline, supply local model paths.

**Section sources**
- [README.md](file://README.md#L42-L48)
- [src/vllm_wizard/hardware/detect.py](file://src/vllm_wizard/hardware/detect.py#L10-L72)

## Installation Methods
Install vLLM Config Wizard using pip from the repository root. Choose the installation variant that matches your needs:

- Base installation (recommended for most users)
  - Command: pip install -e .
- Development installation (includes testing and linting tools)
  - Command: pip install -e ".[dev]"
- Web UI installation (adds FastAPI and web server dependencies)
  - Command: pip install -e ".[web]"

Notes:
- The editable install (-e) ensures changes to the source code take effect immediately without reinstalling.
- The optional web installation adds FastAPI, Uvicorn, and Jinja2 for a local web interface.

**Section sources**
- [README.md](file://README.md#L13-L24)
- [pyproject.toml](file://pyproject.toml#L37-L47)

## Platform-Specific Guidance
- Linux (First-class support)
  - GPU detection via nvidia-smi is fully supported.
  - Ensure nvidia-smi is installed and accessible in PATH.
- macOS (Best-effort)
  - GPU detection may not work; provide manual hardware parameters (--gpu, --vram-gb).
  - The CLI remains functional for planning and artifact generation.
- Windows (Best-effort)
  - GPU detection may not work; provide manual hardware parameters.
  - The CLI remains functional for planning and artifact generation.

**Section sources**
- [requirements.txt](file://requirements.txt#L42-L47)
- [README.md](file://README.md#L42-L47)

## Environment Setup
We strongly recommend using a virtual environment to isolate dependencies:

- Create a virtual environment:
  - python -m venv venv
- Activate the environment:
  - Linux/macOS: source venv/bin/activate
  - Windows: venv\Scripts\activate
- Install the tool:
  - Base: pip install -e .
  - With development tools: pip install -e ".[dev]"
  - With web UI: pip install -e ".[web]"

Benefits:
- Prevents conflicts with system Python packages
- Simplifies uninstallation and upgrades
- Keeps development and production setups separate

**Section sources**
- [README.md](file://README.md#L13-L24)
- [pyproject.toml](file://pyproject.toml#L37-L47)

## Verification and First Run
After installation, verify your setup:

- Check CLI availability:
  - vllm-wizard --help
- Verify GPU detection:
  - vllm-wizard detect
  - On systems without nvidia-smi, this will print a message indicating no NVIDIA GPUs were detected; you can still proceed by providing manual hardware parameters.
- Run a quick planning example:
  - vllm-wizard plan --model meta-llama/Llama-2-7b-hf --json

Expected outcomes:
- The CLI help displays available commands and options.
- The detect command lists GPUs when nvidia-smi is available; otherwise, it advises installing nvidia-smi or providing manual hardware parameters.
- The plan command returns a JSON feasibility report when using --json.

**Section sources**
- [README.md](file://README.md#L26-L62)
- [src/vllm_wizard/cli.py](file://src/vllm_wizard/cli.py#L62-L80)
- [src/vllm_wizard/hardware/detect.py](file://src/vllm_wizard/hardware/detect.py#L10-L72)

## Dependency Management
Core dependencies (always required):
- pydantic>=2.0
- typer>=0.12
- rich>=13.0
- pyyaml>=6.0
- huggingface_hub>=0.20

Development dependencies (optional):
- pytest>=8.0
- pytest-cov>=4.0
- ruff>=0.3

Web UI dependencies (optional):
- fastapi>=0.110
- uvicorn>=0.28
- jinja2>=3.1

Notes:
- The base installation includes core dependencies.
- Development installation adds testing and linting tools.
- Web UI installation adds FastAPI stack for a local web interface.

**Section sources**
- [pyproject.toml](file://pyproject.toml#L29-L47)
- [requirements.txt](file://requirements.txt#L449-L457)

## Troubleshooting Common Issues
- nvidia-smi not found
  - Symptom: vllm-wizard detect prints a message indicating no NVIDIA GPUs detected.
  - Resolution: Install NVIDIA drivers and ensure nvidia-smi is available in PATH. On macOS/Windows, GPU detection may not work; provide manual hardware parameters.
- Python version too old
  - Symptom: Installation fails with a Python version requirement error.
  - Resolution: Upgrade to Python 3.9 or newer.
- Permission errors during installation
  - Symptom: pip install fails with permission errors.
  - Resolution: Use a virtual environment or install with --user flag.
- Missing model metadata
  - Symptom: Errors when using Hugging Face model IDs without internet access.
  - Resolution: Provide a local model path or ensure network connectivity to Hugging Face Hub.
- Web UI startup issues
  - Symptom: No web command found or web server fails to start.
  - Resolution: Install the web optional dependencies and ensure FastAPI/Uvicorn/Jinja2 are available.

**Section sources**
- [src/vllm_wizard/hardware/detect.py](file://src/vllm_wizard/hardware/detect.py#L10-L72)
- [pyproject.toml](file://pyproject.toml#L11-L11)
- [requirements.txt](file://requirements.txt#L486-L493)

## Conclusion
You now have the complete picture for installing and setting up vLLM Config Wizard. Use the base installation for everyday use, the development installation for contributing or testing, and the web installation for a local web interface. Follow the platform-specific guidance for macOS and Windows, ensure nvidia-smi is available for automatic GPU detection, and leverage virtual environments for clean dependency management.