"""Target requirements configuration (config/targets/)."""

from litespec.targets.loader import (
    TargetRequirements,
    available_targets,
    fetch_source,
    integration_dir,
    integration_path,
    isir_output_dir,
    load_target,
    resolve_target,
    resolved_integration_files,
    rust_target_dir,
    source_dir,
    target_config_dir,
    target_entrypoint,
    third_party_dir,
)

__all__ = [
    "TargetRequirements",
    "available_targets",
    "fetch_source",
    "integration_dir",
    "integration_path",
    "isir_output_dir",
    "load_target",
    "resolve_target",
    "resolved_integration_files",
    "rust_target_dir",
    "source_dir",
    "target_config_dir",
    "target_entrypoint",
    "third_party_dir",
]
