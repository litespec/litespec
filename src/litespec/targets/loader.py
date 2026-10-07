"""Target requirements configuration.

Loads per-target requirements from ``config/targets/<name>.yaml`` and drives
source retrieval, extraction, ISIR emission, and completeness checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_TARGET = "liteos"


@dataclass
class TestingConfig:
    """Target-level testing/verification configuration (generic pipeline)."""

    differential_compiler: str = "clang"
    input_domains: list[int] = field(default_factory=lambda: [0, 1, 2, 7, 64, 128])
    max_inputs: int = 64
    fail_on_mismatch: bool = True
    required_differential: list[str] = field(default_factory=list)
    generated_tests_output: str = ""  # empty → do not generate a pytest module

    @classmethod
    def from_dict(cls, d: dict | None) -> TestingConfig:
        if not d:
            return cls()
        diff = d.get("differential", {}) or {}
        cov = d.get("coverage", {}) or {}
        gen = d.get("generated_tests", {}) or {}
        return cls(
            differential_compiler=diff.get("compiler", "clang"),
            input_domains=list(diff.get("input_domains", [0, 1, 2, 7, 64, 128])),
            max_inputs=int(diff.get("max_inputs", 64)),
            fail_on_mismatch=bool(cov.get("fail_on_mismatch", True)),
            required_differential=list(cov.get("required_differential", [])),
            generated_tests_output=gen.get("output", ""),
        )


@dataclass
class TargetRequirements:
    name: str
    source_repo: str
    source_commit: str
    modules: dict[str, list[str]] = field(default_factory=dict)
    source_dir: str = "examples"
    isir_output_dir: str = "output/isir"
    rust_target_dir: str = ""  # Rust port root; empty → targets/<port_name> (board support)
    type_model: str = "default"
    port_name: str = ""  # name for the ported Rust crate/module (e.g. "rliteos")
    manifest_repo: str = ""  # full OpenHarmony manifest (for `repo init`)
    manifest_branch: str = "master"
    preprocess_defines: dict[str, object] = field(default_factory=dict)
    preprocess_include_dirs: list[str] = field(default_factory=list)
    preprocess_empty_macros: list[str] = field(default_factory=list)  # section/attribute macros defined empty
    mmio_read_macros: list[str] = field(default_factory=list)  # C macro names for volatile MMIO reads
    mmio_write_macros: list[str] = field(default_factory=list)  # C macro names for volatile MMIO writes
    target_triple: str = ""  # Rust/LLVM target triple for bare-metal build (e.g. armv7a-none-eabi)
    mcpu: str = ""  # arch -mcpu/-march flag (e.g. "cortex-a15"); empty → omit the flag
    asm_files: list[str] = field(default_factory=list)  # arch .S files, relative to the repo root
    linker_script: str = ""  # linker script path, relative to the repo root
    uart_stub: str = ""  # UART MMIO stub path, relative to the repo root
    build_system: str = ""  # OpenHarmony build system (e.g. "gn")
    build_template: str = ""  # BUILD.gn template path, relative to the repo root
    qemu_machine: str = ""  # QEMU -machine value
    qemu_cpu: str = ""  # QEMU -cpu value
    qemu_memory: str = ""  # QEMU -m value
    entrypoint: str = ""  # target command entry point (targets/<port>/run.sh), repo-relative
    interface_contracts: list[dict] = field(default_factory=list)  # {fn, spec} arch-neutral contracts
    memory_config: dict = field(default_factory=dict)  # memory/PTE descriptor model (page size, levels)
    testing: TestingConfig = field(default_factory=TestingConfig)

    def module_names(self) -> list[str]:
        return list(self.modules.keys())

    def functions_in_scope(self) -> list[str]:
        return [fn for fns in self.modules.values() for fn in fns]

    def functions_for_module(self, module: str) -> list[str]:
        return self.modules.get(module, [])

    def module_for_function(self, function: str) -> Optional[str]:
        for module, fns in self.modules.items():
            if function in fns:
                return module
        return None


def type_model_for(target: TargetRequirements):
    from litespec.type_mapping import load_type_model

    return load_type_model(target.type_model)


def target_config_dir() -> Path:
    return _PROJECT_ROOT / "config" / "targets"


def available_targets() -> list[str]:
    d = target_config_dir()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.yaml"))


def load_target(name: str = _DEFAULT_TARGET) -> TargetRequirements:
    """Load a target's requirements from ``config/targets/<name>.yaml``."""
    path = target_config_dir() / f"{name}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    t = data.get("target", data)
    return TargetRequirements(
        name=t.get("name", name),
        source_repo=t.get("source_repo", ""),
        source_commit=t.get("source_commit", ""),
        manifest_repo=t.get("manifest_repo", ""),
        manifest_branch=t.get("manifest_branch", "master"),
        modules={m: list(fns) for m, fns in (t.get("modules") or {}).items()},
        source_dir=t.get("source_dir", "examples"),
        isir_output_dir=t.get("isir_output_dir", "output/isir"),
        rust_target_dir=t.get("rust_target_dir", ""),
        type_model=t.get("type_model", "default"),
        port_name=t.get("port_name", ""),
        preprocess_defines=dict(t.get("preprocess", {}).get("defines", {})),
        preprocess_include_dirs=list(t.get("preprocess", {}).get("include_dirs", [])),
        preprocess_empty_macros=list(t.get("preprocess", {}).get("empty_macros", [])),
        mmio_read_macros=list(t.get("mmio", {}).get("read_macros", [])),
        mmio_write_macros=list(t.get("mmio", {}).get("write_macros", [])),
        target_triple=t.get("arch", {}).get("target_triple", ""),
        mcpu=t.get("arch", {}).get("mcpu", ""),
        asm_files=list(t.get("arch", {}).get("asm_files", [])),
        linker_script=t.get("arch", {}).get("linker_script", ""),
        uart_stub=t.get("arch", {}).get("uart_stub", ""),
        build_system=t.get("build", {}).get("build_system", ""),
        build_template=t.get("build", {}).get("template", ""),
        qemu_machine=t.get("qemu", {}).get("machine", ""),
        qemu_cpu=t.get("qemu", {}).get("cpu", ""),
        qemu_memory=t.get("qemu", {}).get("memory", ""),
        entrypoint=t.get("entrypoint", ""),
        interface_contracts=list(t.get("interface", {}).get("contracts", [])),
        memory_config=dict(t.get("memory", {})),
        testing=TestingConfig.from_dict(t.get("testing")),
    )


def resolve_target(name: Optional[str] = None) -> str:
    """Resolve the target name: explicit arg → ``LITESPEC_TARGET`` → sole target → default."""
    import os

    if name:
        return name
    env = os.environ.get("LITESPEC_TARGET")
    if env:
        return env
    targets = available_targets()
    if len(targets) == 1:
        return targets[0]
    return _DEFAULT_TARGET


def source_dir(target: TargetRequirements) -> Path:
    return _PROJECT_ROOT / target.source_dir


def isir_output_dir(target: TargetRequirements) -> Path:
    return _PROJECT_ROOT / target.isir_output_dir


def rust_target_dir(target: TargetRequirements) -> Path:
    """The target's Rust port root (``targets/<port_name>`` by default)."""
    if not target.rust_target_dir:
        return integration_dir(target)
    return _PROJECT_ROOT / target.rust_target_dir


def third_party_dir(target: TargetRequirements) -> Path:
    return _PROJECT_ROOT / "third_party" / target.name


def integration_dir(target: TargetRequirements) -> Path:
    """The target's board-support directory (``targets/<port_name>/``)."""
    return _PROJECT_ROOT / "targets" / target.port_name


def integration_path(target: TargetRequirements, rel: str) -> Path:
    """Resolve a config-relative integration path (arch/build/qemu) to an absolute path."""
    return _PROJECT_ROOT / rel


def resolved_integration_files(target: TargetRequirements) -> dict[str, Path]:
    """Map each config-declared integration artifact to its resolved path."""
    out: dict[str, Path] = {}
    for rel in target.asm_files:
        out[rel] = integration_path(target, rel)
    for key in ("linker_script", "uart_stub", "build_template", "entrypoint"):
        rel = getattr(target, key)
        if rel:
            out[rel] = integration_path(target, rel)
    return out


def target_entrypoint(target: TargetRequirements | None = None) -> Path | None:
    """Resolve the target's command entry point (``targets/<port>/run.sh``).

    With no argument, resolves the active target (explicit arg → ``LITESPEC_TARGET``
    → sole target). Returns ``None`` if the target declares no entry point.
    """
    if target is None:
        target = load_target(resolve_target())
    if not target.entrypoint:
        return None
    return integration_path(target, target.entrypoint)


def fetch_source(target: TargetRequirements, dest: Optional[Path] = None) -> Path:
    """Clone ``source_repo`` and check out ``source_commit`` into the third-party tree."""
    import subprocess

    if not target.source_repo or not target.source_commit:
        raise ValueError(f"target {target.name!r} has no source_repo/source_commit")
    dest = dest or third_party_dir(target)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Shallow clone the default branch, then explicitly fetch + checkout the pinned
    # commit. A full clone can fail against partial/lazy mirrors with
    # "fatal: unable to read tree (<sha>)"; fetching the commit by SHA guarantees
    # its tree/blob objects are present.
    subprocess.run(["git", "clone", "--depth", "1", target.source_repo, str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin", target.source_commit], check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "--detach", target.source_commit], check=True)
    return dest
