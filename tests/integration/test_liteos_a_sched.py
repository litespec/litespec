"""Integration tests for the ported LiteOS-A scheduler core (los_sched.c)."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

SRC = Path("/tmp/los_sched_combined.c")
if not SRC.exists():
    SRC = None
SRC2 = Path("/tmp/los_sched2_combined.c")
if not SRC2.exists():
    SRC2 = None
SRC3 = Path("/tmp/los_sched3_combined.c")
if not SRC3.exists():
    SRC3 = None
SRC4 = Path("/tmp/los_sched4_combined.c")
if not SRC4.exists():
    SRC4 = None


def _fns(src: bytes) -> list[str]:
    seen: set[str] = set()
    out = []
    for f in functions(parse_c(src)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            out.append(f.name)
    return out


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A sched source not present")
def test_sched_policy_switch_and_compare():
    src = SRC.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  let t1: u32 = 0x2000; let t2: u32 = 0x3000;\n"
        '  println!("i1={}", OsSchedParamInit(t1, 1, 0, 0));\n'  # FIFO → HPF
        '  println!("i2={}", OsSchedParamInit(t1, 2, 0, 0));\n'  # RR → HPF
        '  println!("i6={}", OsSchedParamInit(t1, 6, 0, 0));\n'  # DEADLINE → EDF
        '  println!("i3={}", OsSchedParamInit(t1, 3, 0, 0));\n'  # IDLE
        '  println!("i99={}", OsSchedParamInit(t1, 99, 0, 0));\n'  # default → LOS_NOK
        '  __write(t1+0, 3); __write(t2+0, 0); println!("c1={}", OsSchedParamCompare(t1, t2));\n'
        '  __write(t1+0, 0); __write(t2+0, 3); println!("c2={}", OsSchedParamCompare(t1, t2));\n'
        '  __write(t1+0, 1); __write(t2+0, 1); println!("c3={}", OsSchedParamCompare(t1, t2));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "sched.rs"
        exe = Path(d) / "sched"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "i1=0"  # FIFO → LOS_OK
        assert out[1] == "i2=0"  # RR → LOS_OK
        assert out[2] == "i6=0"  # DEADLINE → LOS_OK
        assert out[3] == "i3=0"  # IDLE → LOS_OK
        assert out[4] == "i99=1"  # default → LOS_NOK
        assert out[5] == "c1=0"  # ops->schedParamCompare stub → 0
        assert out[6] == "c2=0"  # ops->schedParamCompare stub → 0
        assert out[7] == "c3=0"  # same policy → ops->schedParamCompare stub


@pytest.mark.skipif(SRC2 is None, reason="real LiteOS-A sched source not present")
def test_sched_runqueue_bootstrap():
    # OsSchedRunqueueInit/IdleInit/OsSchedInit: struct-pointer array indexing (g_schedRunqueue[i]).
    src = SRC2.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    assert "wrapping_mul(14)" in rust  # &g_schedRunqueue[i] scales by sizeof(SchedRunqueue)
    rust += (
        "\nfn main() { unsafe {\n"
        "  g_schedRunqueue = 0x4000;\n"
        "  OsSchedRunqueueInit();\n"
        '  println!("r0={:#x}", __read(0x4000 + 9));\n'
        '  println!("r1={:#x}", __read(0x4000 + 23));\n'
        "  OsSchedRunqueueIdleInit(0x1234);\n"
        '  println!("idle={:#x}", __read(0x4000 + 11));\n'
        '  println!("init={}", OsSchedInit());\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "sched2.rs"
        exe = Path(d) / "sched2"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "r0=0xffffffff"  # responseTime = OS_SCHED_MAX_RESPONSE_TIME
        assert out[1] == "r1=0x0"  # core 1 uninitialized (LOSCFG_KERNEL_CORE_NUM = 1)
        assert out[2] == "idle=0x1234"  # idleTask set
        assert out[3] == "init=0"  # OsSchedInit → LOS_OK


@pytest.mark.skipif(SRC3 is None, reason="real LiteOS-A sched source not present")
def test_sched_start_resched_schedule():
    # OsSchedStart/OsSchedResched/LOS_Schedule: taskStatus |= RUNNING, schedFlag clear, no-switch short-circuit.
    src = SRC3.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  g_schedRunqueue = 0x4000;\n"
        "  __write(0x4000+7, 0x6000); __write(0x4000+8, 0x5000); __write(0x4000+11, 0x2000);\n"
        "  __write(0x5000+0, 0x5000); __write(0x5000+1, 0x5000);\n"
        "  __write(0x6000+3104, 0);\n"
        "  __write(0x2000+1, 0); __write(0x4000+13, 0xF);\n"
        "  OsSchedStart();\n"
        '  println!("ts={:#x} st={} rid={:#x}", __read(0x2000+1), __read(0x2000+2), __read(0x4000+10));\n'
        "  OsSchedResched();\n"
        '  println!("flag={:#x}", __read(0x4000+13));\n'
        "  LOS_Schedule();\n"
        '  println!("ok");\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "sched3.rs"
        exe = Path(d) / "sched3"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "ts=0x4"  # taskStatus |= OS_TASK_STATUS_RUNNING
        assert out[1] == "st=0"  # startTime = OsGetCurrSchedTimeCycle() (0)
        assert out[2] == "rid=0xffffffff"  # responseID = OS_INVALID
        assert out[3] == "flag=0xc"  # schedFlag &= ~INT_PEND_RESCH (0xF → 0xC)
        assert out[4] == "ok"


@pytest.mark.skipif(SRC4 is None, reason="real LiteOS-A sched source not present")
def test_sched_top_task_pick_next():
    # TopTaskGet / HPFRunqueueTopTaskGet: CLZ bitmap scan + EDF/HPF/idle fallback.
    src = SRC4.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  let rq: u32 = 0x4000; __write(rq+7, 0x6000); __write(rq+8, 0x5000); __write(rq+11, 0x9000);\n"
        "  __write(0x5000+1, 0x5000);\n"
        "  __write(0x6000+3104, 0x80000000); __write(0x6000+96, 0x80000000); __write(0x6000+1, 0x3037);\n"
        "  __write(0x3000+77, 1);\n"
        '  println!("hpf={}", HPFRunqueueTopTaskGet(0x6000));\n'
        '  println!("top_hpf={}", TopTaskGet(rq));\n'
        "  __write(0x5000+1, 0x2037);\n"
        '  println!("top_edf={}", TopTaskGet(rq));\n'
        "  __write(0x5000+1, 0x5000); __write(0x6000+3104, 0);\n"
        '  println!("top_idle={}", TopTaskGet(rq));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "sched4.rs"
        exe = Path(d) / "sched4"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "hpf=12288"  # HPF top task = 0x3000 (CLZ scan)
        assert out[1] == "top_hpf=12288"  # EDF empty → HPF
        assert out[2] == "top_edf=8192"  # EDF non-empty → 0x2000
        assert out[3] == "top_idle=36864"  # both empty → idle 0x9000
