"""Integration tests for the ported LiteOS-A task core (los_task.c).

Verifies the self-contained task-management paths (param check) and the struct
handling that the scheduler/task core needs.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from litespec.extraction import parse_c
from litespec.extraction.c_translation_unit import functions
from litespec.extraction.config import Config
from litespec.extraction.size_table import compute_sizes
from litespec.extraction.struct_table import StructTable
from litespec.lowering import port_module
from litespec.type_mapping import load_type_model

SRC = Path("/tmp/los_task_combined.c")
if not SRC.exists():
    SRC = None
SRC2 = Path("/tmp/los_task2_combined.c")
if not SRC2.exists():
    SRC2 = None
SRC3 = Path("/tmp/los_task3_combined.c")
if not SRC3.exists():
    SRC3 = None
SRC4 = Path("/tmp/los_task4_combined.c")
if not SRC4.exists():
    SRC4 = None
SRC5 = Path("/tmp/los_task5_combined.c")
if not SRC5.exists():
    SRC5 = None


def _fns(src: bytes) -> list[str]:
    seen: set[str] = set()
    out = []
    for f in functions(parse_c(src)):
        if f.name and f.name not in seen:
            seen.add(f.name)
            out.append(f.name)
    return out


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A task source not present")
def test_task_struct_layout():
    src = SRC.read_bytes()
    st = StructTable.from_translation_unit(parse_c(src))
    sizes = compute_sizes(st)
    assert sizes["TSK_INIT_PARAM_S"] == 20
    off = st.scoped_field_offsets(sizes)
    assert off["TSK_INIT_PARAM_S.pfnTaskEntry"] == 0
    assert off["TSK_INIT_PARAM_S.usTaskPrio"] == 1
    assert off["TSK_INIT_PARAM_S.uwStackSize"] == 7
    assert off["TSK_INIT_PARAM_S.pcName"] == 8
    assert off["TSK_INIT_PARAM_S.processID"] == 12


@pytest.mark.skipif(SRC is None, reason="real LiteOS-A task source not present")
def test_task_create_param_check():
    src = SRC.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  let taskID: u32 = 0x1000; let init: u32 = 0x2000;\n"
        "  __write(init+0, 0x1234); __write(init+1, 10); __write(init+7, 0x4000); __write(init+8, 0x5000); __write(init+12, 0);\n"
        '  println!("t1={}", TaskCreateParamCheck(0, init));\n'
        '  println!("t2={}", TaskCreateParamCheck(taskID, 0));\n'
        '  __write(init+8, 0); println!("t3={}", TaskCreateParamCheck(taskID, init));\n'
        '  __write(init+8, 0x5000); __write(init+0, 0); println!("t4={}", TaskCreateParamCheck(taskID, init));\n'
        '  __write(init+0, 0x1234); __write(init+1, 40); println!("t5={}", TaskCreateParamCheck(taskID, init));\n'
        '  __write(init+1, 10); __write(init+7, 0xFFFFFFFF); println!("t6={}", TaskCreateParamCheck(taskID, init));\n'
        '  __write(init+7, 0); println!("t7={}", TaskCreateParamCheck(taskID, init));\n'
        '  __write(init+7, 64); println!("t8={}", TaskCreateParamCheck(taskID, init));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "task.rs"
        exe = Path(d) / "task"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = dict(t.split("=") for t in run.stdout.split())
        assert out["t1"] == "33554951"  # taskID == NULL → LOS_ERRNO_TSK_ID_INVALID
        assert out["t2"] == "33554945"  # initParam == NULL → LOS_ERRNO_TSK_PTR_NULL
        assert out["t3"] == "33554949"  # pcName == NULL → LOS_ERRNO_TSK_NAME_EMPTY
        assert out["t4"] == "33554948"  # pfnTaskEntry == NULL → LOS_ERRNO_TSK_ENTRY_NULL
        assert out["t5"] == "33554947"  # usTaskPrio > 31 → LOS_ERRNO_TSK_PRIOR_ERROR
        assert out["t6"] == "33554976"  # uwStackSize > pool → LOS_ERRNO_TSK_STKSZ_TOO_LARGE
        assert out["t7"] == "0"  # stack defaulted+aligned → LOS_OK
        assert out["t8"] == "33554950"  # stack < min → LOS_ERRNO_TSK_STKSZ_TOO_SMALL


@pytest.mark.skipif(SRC2 is None, reason="real LiteOS-A task source not present")
def test_task_cb_base_init_and_container_of():
    src = SRC2.read_bytes()
    st = StructTable.from_translation_unit(parse_c(src))
    sizes = compute_sizes(st)
    off = st.scoped_field_offsets(sizes)
    assert sizes["LosTaskCB"] == 85
    assert off["LosTaskCB.stackPointer"] == 0
    assert off["LosTaskCB.taskStatus"] == 1
    assert off["LosTaskCB.args"] == 19
    assert off["LosTaskCB.pendList"] == 55

    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    # container_of: OS_TCB_FROM_PENDLIST(ptr) = ptr - offsetof(pendList) = ptr - 55
    assert "wrapping_sub(55)" in rust
    rust += (
        "\nfn main() { unsafe {\n"
        "  let taskCB: u32 = 0x2000; let init: u32 = 0x3000;\n"
        "  __write(init+0, 0x1234);\n"
        "  __write(init+3, 0x111); __write(init+4, 0x222); __write(init+5, 0x333); __write(init+6, 0x444);\n"
        "  __write(init+7, 0x4000); __write(init+10, 0x80000000);\n"
        "  TaskCBBaseInit(taskCB, init);\n"
        '  println!("sp={} a={:#x},{:#x},{:#x},{:#x}", __read(taskCB+0), __read(taskCB+19), __read(taskCB+20), __read(taskCB+21), __read(taskCB+22));\n'
        '  println!("stack={:#x} entry={:#x} status={:#x}", __read(taskCB+12), __read(taskCB+15), __read(taskCB+1));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "task2.rs"
        exe = Path(d) / "task2"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "sp=0"  # stackPointer = NULL
        assert out[1] == "a=0x111,0x222,0x333,0x444"  # args[0..3] copied from auwArgs
        assert out[2] == "stack=0x4000"  # stackSize = uwStackSize
        assert out[3] == "entry=0x1234"  # taskEntry = pfnTaskEntry
        assert out[4] == "status=0x801"  # INIT | JOINABLE flag set (uwResved & LOS_TASK_ATTR_JOINABLE)


@pytest.mark.skipif(SRC3 is None, reason="real LiteOS-A task source not present")
def test_task_create_only_full_path():
    # LOS_TaskCreateOnly: param check → GetFreeTaskCB (container_of) → TaskCBInit →
    # TaskStackInit → *taskID = taskCB->taskID (output param round-trip).
    src = SRC3.read_bytes()
    rust = port_module(
        src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True,
        mock_returns={"OsTaskStackInit": 0x5000},
    )
    rust += (
        "\nfn main() { unsafe {\n"
        "  let tcb: u32 = 0x2000;\n"
        "  __write(tcb+14, 42);\n"
        "  __write(tcb+55, 0); __write(tcb+56, 0);\n"
        "  __write(0, tcb+55); __write(1, tcb+55);\n"
        "  let taskID_slot: u32 = 0x4000; let init: u32 = 0x3000;\n"
        "  __write(init+0, 0x1234); __write(init+1, 10); __write(init+7, 0x4000); __write(init+8, 0x5000); __write(init+12, 0);\n"
        "  let ret = LOS_TaskCreateOnly(taskID_slot, init);\n"
        '  println!("ret={} taskID={} sp={:#x} tos={:#x}", ret, __read(taskID_slot), __read(tcb+0), __read(tcb+13));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "task3.rs"
        exe = Path(d) / "task3"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "ret=0"  # LOS_OK
        assert out[1] == "taskID=42"  # *taskID = taskCB->taskID (output param)
        assert out[2] == "sp=0x5000"  # stackPointer = OsTaskStackInit stub
        assert out[3] == "tos=0x3000"  # topOfStack = LOS_MemAllocAlign bump allocator (base)


@pytest.mark.skipif(SRC4 is None, reason="real LiteOS-A task source not present")
def test_os_task_init_boot():
    # OsTaskInit: sizeof(LosTaskCB) + struct-pointer array indexing (g_taskCBArray[i]).
    src = SRC4.read_bytes()
    rust = port_module(src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True)
    rust += (
        "\nfn main() { unsafe {\n"
        "  let ret = OsTaskInit(0x1234);\n"
        '  println!("ret={} max={} arr={}", ret, g_taskMaxNum, g_taskCBArray);\n'
        "  let base = g_taskCBArray;\n"
        '  for i in 0..4u32 { let cb = base + i * 85; println!("s={:#x},id={},p={:#x}", __read(cb+1), __read(cb+14), __read(cb+78)); }\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "task4.rs"
        exe = Path(d) / "task4"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "ret=0"
        assert out[1] == "max=128"  # LOSCFG_BASE_CORE_TSK_LIMIT
        assert out[2] == "arr=12288"  # LOS_MemAlloc stub (0x3000)
        assert out[3] == "s=0x400,id=0,p=0x1234"  # TCB[0]: UNUSED, id 0, processCB
        assert out[4] == "s=0x400,id=1,p=0x1234"
        assert out[5] == "s=0x400,id=2,p=0x1234"
        assert out[6] == "s=0x400,id=3,p=0x1234"


@pytest.mark.skipif(SRC5 is None, reason="real LiteOS-A task source not present")
def test_task_create_public_wrapper():
    # LOS_TaskCreate: processID assignment + OS_TCB_FROM_TID (struct-pointer arithmetic on a global).
    src = SRC5.read_bytes()
    rust = port_module(
        src, _fns(src), type_model=load_type_model("liteos"), config=Config(), executable=True,
        mock_returns={"OsTaskStackInit": 0x5000},
    )
    assert "wrapping_mul(85)" in rust  # OS_TCB_FROM_TID scales by sizeof(LosTaskCB) = 85 words
    rust += (
        "\nfn main() { unsafe {\n"
        "  let taskID_slot: u32 = 0x4000; __write(taskID_slot, 42);\n"
        "  let tcb: u32 = 0x2000;\n"
        "  __write(tcb+55, 0); __write(tcb+56, 0);\n"
        "  __write(0, tcb+55); __write(1, tcb+55);\n"
        "  let init: u32 = 0x3000; __write(init+0, 0x1234); __write(init+8, 0x5000); __write(init+12, 0);\n"
        "  let ret = LOS_TaskCreate(taskID_slot, init);\n"
        '  println!("ret={} pid={:#x} tid={}", ret, __read(init+12), __read(taskID_slot));\n'
        "} }\n"
    )
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as d:
        srcf = Path(d) / "task5.rs"
        exe = Path(d) / "task5"
        srcf.write_text(rust, encoding="utf-8")
        proc = subprocess.run(["rustc", "--edition", "2021", str(srcf), "-o", str(exe)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        out = run.stdout.split()
        assert out[0] == "ret=0"
        assert out[1] == "pid=0x0"  # processID = OsCurrProcessGet() (NULL stub)
        assert out[2] == "tid=0"  # taskCB->taskID assigned by OsProcessAddNewTask (NULL stub)
