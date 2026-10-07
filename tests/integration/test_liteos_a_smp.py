"""Integration tests for the SMP primitives (atomics + current-CPU cell).

Exercises the ``LOS_Atomic*`` and ``ArchCurrCpuid`` intrinsics end-to-end through
the full pipeline (extract → lower → Rust → run), while the main target config
keeps ``LOSCFG_KERNEL_SMP`` off — this is the "single-core SMP" baseline.
"""

import subprocess
import tempfile
from pathlib import Path

from litespec.extraction.config import Config
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

# A minimal C unit that calls the atomic/CPUID intrinsics (their bodies are the
# real inline-asm ones we abstract away; here we only exercise the *call sites*).
SRC = (
    "typedef struct { volatile unsigned int counter; } Atomic;\n"
    "unsigned int smp_atomic_test(Atomic *v, unsigned int addVal, unsigned int newVal, unsigned int oldVal) {\n"
    "    unsigned int a = LOS_AtomicAdd(v, addVal);\n"
    "    LOS_AtomicInc(v);\n"
    "    unsigned int d = LOS_AtomicDecRet(v);\n"
    "    unsigned int c = LOS_AtomicCmpXchg32bits(v, newVal, oldVal);\n"
    "    unsigned int cpuid = ArchCurrCpuid();\n"
    "    return a + d + c + cpuid;\n"
    "}\n"
)


def _run(main: str) -> str:
    rust = port_module(SRC.encode(), ["smp_atomic_test"], type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += main
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "smp.rs"
        exe = Path(d) / "smp"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        return run.stdout


def test_atomic_fetch_and_cmpxchg_semantics():
    # counter=10; add 5 (→15, returns 10); inc (→16); dec-ret (→15, returns 15);
    # cmpxchg(9, 99) no-match (returns 0); cpuid=0 → return 10+15+0+0 = 25.
    out = _run(
        "\nfn main() { unsafe {\n"
        "  __write(0x100, 10);\n"
        '  let r = smp_atomic_test(0x100, 5, 9, 99);\n'
        '  println!("r={} v={}", r, __read(0x100));\n'
        "} }\n"
    )
    assert out.split() == ["r=25", "v=15"]


def test_atomic_cmpxchg_swaps_on_match():
    # counter=99; add 0 (→99, returns 99); inc (→100); dec-ret (→99, returns 99);
    # cmpxchg(9, 99) matches → counter=9 (returns 1); cpuid=0 → 99+99+1+0 = 199.
    out = _run(
        "\nfn main() { unsafe {\n"
        "  __write(0x100, 99);\n"
        '  let r = smp_atomic_test(0x100, 0, 9, 99);\n'
        '  println!("r={} v={}", r, __read(0x100));\n'
        "} }\n"
    )
    assert out.split() == ["r=199", "v=9"]


def test_curr_cpuid_cell():
    # The current-CPU-id is a model cell; setting it makes ArchCurrCpuid() read it.
    out = _run(
        "\nfn main() { unsafe {\n"
        "  __write_curr_cpuid(2);\n"
        "  __write(0x100, 10);\n"
        '  let r = smp_atomic_test(0x100, 5, 9, 99);\n'
        '  println!("r={}", r);\n'
        "} }\n"
    )
    assert out.split() == ["r=27"]  # 10+15+0+2 (cpuid=2)
