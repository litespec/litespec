"""Arch-neutral interface contracts for cross-arch equivalence checking.

A contract declares the *observable* behavior of an arch entry point (e.g. the MMU
page-table walk) independently of the descriptor format. Each arch is checked against
the same contract; two archs are "equivalent" when they both pass the same contract,
rather than by comparing their (necessarily different) C bodies.

Each spec is a function ``(c_source: bytes, fn_name: str, tm) -> ContractResult`` that
ports the function and its callee closure, drives it with bounded scenarios, and
reports pass/fail. The check logic lives here once; archs only *declare conformance*
in their target config (``interface.contracts``).
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ContractResult:
    contract: str
    fn: str
    status: str  # "pass" | "fail" | "unavailable"
    reports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"contract": self.contract, "fn": self.fn, "status": self.status, "reports": self.reports}


#: spec name → check(c_source, fn_name, tm) -> ContractResult
_CONTRACTS: dict[str, callable] = {}


def register(spec: str):
    def deco(fn):
        _CONTRACTS[spec] = fn
        return fn

    return deco


def _port_and_run(c_source: bytes, closure: set[str], tm, main: str) -> str:
    """Port ``closure`` functions from ``c_source``, append ``main``, compile and run."""
    from litespec.extraction import parse_c
    from litespec.extraction.c_translation_unit import functions
    from litespec.extraction.config import Config
    from litespec.lowering import port_module

    seen: set[str] = set()
    fns = []
    for f in functions(parse_c(c_source)):
        if f.name and f.name not in seen and f.name in closure:
            seen.add(f.name)
            fns.append(f.name)
    rust = port_module(c_source, fns, type_model=tm, config=Config(), executable=True)
    rust += main
    with tempfile.TemporaryDirectory() as d:
        srcf = Path(d) / "contract.rs"
        exe = Path(d) / "contract"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"contract port failed to compile: {proc.stderr[-500:]}")
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        if run.returncode != 0:
            raise RuntimeError(f"contract scenario panicked: {run.stderr[-500:]}")
        return run.stdout


def _field_offset(c_source: bytes, dotted: str) -> int | None:
    from litespec.extraction import parse_c
    from litespec.extraction.size_table import compute_sizes
    from litespec.extraction.struct_table import StructTable

    st = StructTable.from_translation_unit(parse_c(c_source))
    sizes = compute_sizes(st)
    return st.scoped_field_offsets(sizes).get(dotted)


@register("mmu_query")
def mmu_query(c_source: bytes, fn_name: str, tm, memory: dict | None = None) -> ContractResult:
    """Contract: the MMU page-table walk maps a mapped vaddr → paddr and rejects unmapped.

    Observables: unmapped → ``LOS_ERRNO_VM_NOT_FOUND`` (non-zero); section-mapped →
    ``LOS_OK`` and ``*paddr`` = section base + page offset. The L1 shift/type/frame are
    read from the target's ``memory`` descriptor model (not hardcoded), so x86/RISC-V
    declare different values for the same contract; the field offset is resolved from
    the source so the check is reusable across struct layouts.
    """
    virt_off = _field_offset(c_source, "LosArchMmu.virtTtb")
    if virt_off is None:
        return ContractResult("mmu_query", fn_name, "unavailable", ["LosArchMmu.virtTtb not found"])
    memory = memory or {}
    l1_shift = int(memory.get("l1_index_shift", 20))
    section_type = int(memory.get("l1_section_type", 0x2))
    section_frame = int(memory.get("l1_section_frame", 0xFFF00000))
    section_offset_mask = int(memory.get("l1_section_offset_mask", 0xFFFFF))
    vaddr = 0x400123
    ttb_index = vaddr >> l1_shift
    section_base = 0x12300000  # frame-aligned (low bits below the section frame are clear)
    entry = section_base | section_type
    expected_paddr = (entry & section_frame) + (vaddr & section_offset_mask)
    closure = {
        fn_name,
        "OsGetPte1",
        "OsGetPte1Ptr",
        "OsGetPte1Index",
        "OsIsPte1Invalid",
        "OsIsPte1Section",
        "OsIsPte1PageTable",
        "OsGetPte2",
        "OsGetPte2Index",
        "OsGetPte2BasePtr",
        "OsIsPte2SmallPage",
        "OsIsPte2SmallPageXN",
        "OsIsPte2LargePage",
        "OsCvtSecAttsToFlags",
        "OsCvtPte2AttsToFlags",
        "OsCvtSecFlagsToAttrs",
        "OsCvtSecCacheFlagsToMMUFlags",
        "OsCvtSecAccessFlagsToMMUFlags",
    }
    it = tm.word_type()
    main = (
        "\nfn main() { unsafe {\n"
        f"  let am: {it} = 0x1000; __write(am+{virt_off}, 0x2000);\n"  # archMmu.virtTtb → L1 table
        f"  __write(0x2000+{ttb_index}, 0);\n"  # unmapped: L1 entry invalid → NOT_FOUND
        f"  let s1 = {fn_name}(am, {vaddr}, 0x3000, 0);\n"
        '  println!("s1={} p1={:#x}", s1, __read(0x3000));\n'
        f"  __write(0x2000+{ttb_index}, {entry:#x});\n"  # mapped: L1 section entry
        f"  let s2 = {fn_name}(am, {vaddr}, 0x3000, 0);\n"
        '  println!("s2={} p2={:#x}", s2, __read(0x3000));\n'
        "} }\n"
    )
    try:
        out = _port_and_run(c_source, closure, tm, main)
    except RuntimeError as exc:
        return ContractResult("mmu_query", fn_name, "fail", [str(exc)])
    tokens = out.split()
    s1 = int(tokens[0].split("=")[1])
    p2 = int(tokens[3].split("=")[1], 16)
    reports = []
    reports.append(f"unmapped vaddr → status={s1} (expected non-zero) {'✓' if s1 != 0 else '✗'}")
    reports.append(
        f"section vaddr → paddr={p2:#x} (expected {expected_paddr:#x}) {'✓' if p2 == expected_paddr else '✗'}"
    )
    ok = (s1 != 0) and (p2 == expected_paddr)
    return ContractResult("mmu_query", fn_name, "pass" if ok else "fail", reports)


def run_contract(decl: dict, c_source: bytes, tm, memory: dict | None = None) -> ContractResult:
    spec = decl.get("spec")
    fn = decl.get("fn")
    check = _CONTRACTS.get(spec)
    if check is None:
        return ContractResult(spec, fn or "?", "unavailable", [f"unknown spec: {spec}"])
    return check(c_source, fn, tm, memory)


def verify_contracts(
    c_source: bytes, contracts: list[dict], tm=None, memory: dict | None = None
) -> list[ContractResult]:
    """Run every declared contract of one target against its combined source."""
    if tm is None:
        from litespec.type_mapping import load_type_model

        tm = load_type_model("liteos")
    return [run_contract(c, c_source, tm, memory) for c in contracts]


def compare_contracts(
    a_source: bytes, b_source: bytes, contracts: list[dict], tm_a=None, tm_b=None, memory_a=None, memory_b=None
) -> dict:
    """Run the same contracts on two arch sources and diff the results."""
    from litespec.type_mapping import load_type_model

    ra = verify_contracts(a_source, contracts, tm_a or load_type_model("liteos"), memory_a)
    rb = verify_contracts(b_source, contracts, tm_b or load_type_model("liteos"), memory_b)
    agree = []
    disagree = []
    for ca, cb in zip(ra, rb):
        if ca.status == cb.status == "pass":
            agree.append(ca.contract)
        else:
            disagree.append({"contract": ca.contract, "a": ca.to_dict(), "b": cb.to_dict()})
    return {"agree": agree, "disagree": disagree, "a": [r.to_dict() for r in ra], "b": [r.to_dict() for r in rb]}
