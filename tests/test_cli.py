"""Tests for CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from vllm_wizard.cli import app
from vllm_wizard.schemas.outputs import GPUInfo

runner = CliRunner()


class TestDetectCommand:
    """Tests for the detect command."""

    def test_detect_no_gpus(self):
        """Test detect with no GPUs available."""
        with patch("vllm_wizard.cli.detect_gpus", return_value=[]):
            result = runner.invoke(app, ["detect"])
            assert result.exit_code == 0
            assert "No NVIDIA GPUs detected" in result.stdout

    def test_detect_with_gpus(self):
        """Test detect with GPUs available."""
        mock_gpus = [
            GPUInfo(name="NVIDIA RTX 4090", vram_mib=24576, driver_version="535.86.05"),
            GPUInfo(name="NVIDIA RTX 4090", vram_mib=24576, driver_version="535.86.05"),
        ]

        with patch("vllm_wizard.cli.detect_gpus", return_value=mock_gpus):
            result = runner.invoke(app, ["detect"])
            assert result.exit_code == 0
            assert "RTX 4090" in result.stdout

    def test_detect_json_output(self):
        """Test detect with JSON output."""
        mock_gpus = [
            GPUInfo(name="NVIDIA RTX 4090", vram_mib=24576),
        ]

        with patch("vllm_wizard.cli.detect_gpus", return_value=mock_gpus):
            result = runner.invoke(app, ["detect", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert len(data) == 1
            assert data[0]["name"] == "NVIDIA RTX 4090"


class TestPlanCommand:
    """Tests for the plan command."""

    def test_plan_json_output(self, tmp_config_dir: Path):
        """Test plan command returns valid JSON."""
        mock_gpus = [
            GPUInfo(name="NVIDIA RTX 4090", vram_mib=24576),
        ]

        with patch("vllm_wizard.planning.planner.detect_gpus", return_value=mock_gpus):
            result = runner.invoke(
                app,
                [
                    "plan",
                    "--model", str(tmp_config_dir),
                    "--json",
                    "--params-b", "7",
                ],
            )

            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert "feasibility" in data
            assert "config" in data
            assert "performance" in data
            assert "artifacts" in data

    def test_plan_console_output(self, tmp_config_dir: Path):
        """Test plan command with console output."""
        mock_gpus = [
            GPUInfo(name="NVIDIA RTX 4090", vram_mib=24576),
        ]

        with patch("vllm_wizard.planning.planner.detect_gpus", return_value=mock_gpus):
            result = runner.invoke(
                app,
                [
                    "plan",
                    "--model", str(tmp_config_dir),
                    "--params-b", "7",
                ],
            )

            assert result.exit_code == 0
            assert "VRAM Breakdown" in result.stdout or "Feasibility" in result.stdout

    def test_plan_with_explain(self, tmp_config_dir: Path):
        """Test plan command with explanations."""
        mock_gpus = [
            GPUInfo(name="NVIDIA RTX 4090", vram_mib=24576),
        ]

        with patch("vllm_wizard.planning.planner.detect_gpus", return_value=mock_gpus):
            result = runner.invoke(
                app,
                [
                    "plan",
                    "--model", str(tmp_config_dir),
                    "--json",
                    "--explain",
                    "--params-b", "7",
                ],
            )

            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert data["config"]["explanations"]  # Should have explanations

    def test_plan_no_gpu_error(self, tmp_config_dir: Path):
        """Test plan fails gracefully without GPU."""
        with patch("vllm_wizard.planning.planner.detect_gpus", return_value=[]):
            result = runner.invoke(
                app,
                [
                    "plan",
                    "--model", str(tmp_config_dir),
                ],
            )

            assert result.exit_code == 1
            assert "Error" in result.stdout


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_creates_files(self, tmp_config_dir: Path, tmp_path: Path):
        """Test generate command creates artifact files."""
        mock_gpus = [
            GPUInfo(name="NVIDIA RTX 4090", vram_mib=24576),
        ]
        output_dir = tmp_path / "output"

        with patch("vllm_wizard.planning.planner.detect_gpus", return_value=mock_gpus):
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--output-dir", str(output_dir),
                    "--model", str(tmp_config_dir),
                    "--params-b", "7",
                ],
            )

            assert result.exit_code == 0
            assert (output_dir / "serve_command.sh").exists()
            assert (output_dir / "profile.yaml").exists()
            assert (output_dir / "plan.json").exists()

    def test_generate_with_compose(self, tmp_config_dir: Path, tmp_path: Path):
        """Test generate command with docker-compose."""
        mock_gpus = [
            GPUInfo(name="NVIDIA RTX 4090", vram_mib=24576),
        ]
        output_dir = tmp_path / "output"

        with patch("vllm_wizard.planning.planner.detect_gpus", return_value=mock_gpus):
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--output-dir", str(output_dir),
                    "--model", str(tmp_config_dir),
                    "--emit", "command,profile,compose",
                    "--params-b", "7",
                ],
            )

            assert result.exit_code == 0
            assert (output_dir / "docker-compose.yaml").exists()


class TestVersion:
    """Tests for version flag."""

    def test_version(self):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "vllm-wizard version" in result.stdout
