"""Configuration loader and validator.

Responsible for loading YAML config files, validating required fields,
and resolving output directory paths relative to config file location.
"""
from pathlib import Path
from typing import Any

import yaml


REQUIRED_STUDY_FIELDS = ["topic", "target_species", "reference_species", "entity_type", "behavior"]


def load_config(config_path: str) -> dict[str, Any]:
    """Load YAML configuration file and validate required fields.

    Args:
        config_path: Path to YAML config file.

    Returns:
        Parsed configuration dict.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If required fields are missing or empty.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with path.open() as f:
        config = yaml.safe_load(f)

    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate that all required fields are present and non-empty."""
    study = config.get("study")
    if not study:
        raise ValueError("Missing 'study' section in config")

    for field in REQUIRED_STUDY_FIELDS:
        value = study.get(field)
        if not value:
            raise ValueError(f"study.{field} must be non-empty")

    if not isinstance(study["reference_species"], list) or not study["reference_species"]:
        raise ValueError("study.reference_species must be a non-empty list")

    extraction = config.get("extraction", {})
    if "evidence_levels" not in extraction:
        raise ValueError("extraction.evidence_levels is required (the four-level framework)")


def get_output_dir(config: dict[str, Any], config_path: str) -> Path:
    """Resolve output directory relative to config file location.

    If output.dir is relative, it's resolved relative to the config file's
    parent directory. This keeps outputs alongside the case config.
    """
    output_cfg = config.get("output", {})
    dir_name = output_cfg.get("dir", "output")

    output_dir = Path(dir_name)
    if not output_dir.is_absolute():
        config_dir = Path(config_path).parent
        output_dir = config_dir / output_dir

    return output_dir
