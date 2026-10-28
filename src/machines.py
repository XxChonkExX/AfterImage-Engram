"""machines: the hybrid execution family, one uniform contract.

run(machine, code) -> {"ok", "result", "steps", "err", "machine"}

Every machine is deterministic, capped, and host-isolated. This module
is the registry the router advertises as tools and the engram documents
as ISA manuals.

Machines:
  ti85     - scientific expression calculator (TI syntax)
  pyvm     - Python-subset programs (def solve())
  rv32     - RV32I RISC-V assembly
  z80      - Zilog Z80 assembly (kosarev/z80 core + assembler, MIT)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\Users\mikeh\Documents\New OpenCode Project\AfterImage-Engram\src")

import ti85  # noqa: E402
import pyvm  # noqa: E402
import rv32  # noqa: E402
import thumb2  # noqa: E402
import m6502  # noqa: E402
import dataflow  # noqa: E402
import mathcheck  # noqa: E402


def run_ti85(code):
    r = ti85.calculate(code)
    ok = not r.startswith("ERROR")
    try:
        val = float(r) if ok else None
    except ValueError:
        val = None
    return {"ok": ok, "result": val if val is not None else r,
            "steps": 1, "err": None if ok else r}


def run_pyvm(code):
    return pyvm.run_py(code)


def run_rv32(code):
    return rv32.run_asm(code, max_steps=50000)


def run_m6502(code):
    """Assemble + execute 6502 source; result = A at BRK."""
    try:
        return m6502.run(code)
    except Exception as e:
        return {"ok": False, "err": f"assemble: {e}", "steps": 0,
                "result": None}


def run_thumb2(code):
    return thumb2.run_asm(code, max_steps=50000)


def run_dataflow(code):
    return dataflow.run_graph(code)


def run_z80(code):
    """Assemble + execute Z80 source; result = byte at 0x8000."""
    from z80 import Asm, SourceFile, Z80Machine
    try:
        code_obj = Asm().assemble(SourceFile("prog.z80", code))
        code_obj.resolve()
        loaded = code_obj.encode()
    except Exception as e:
        return {"ok": False, "err": f"assemble: {e}", "steps": 0,
                "result": None}
    m = Z80Machine()
    for addr, image in loaded:
        m.set_memory_block(addr, image)
        if addr <= 0x8000 < addr + len(image):
            pass
    # place a result sentinel so we can detect writes to 0x8000
    m.pc = min(a for a, _ in loaded)
    m.ticks_to_stop = 50_000_000
    try:
        m.run()
    except Exception as e:
        return {"ok": False, "err": f"run: {e}", "steps": m.ticks_to_stop,
                "result": None}
    b = m.memory.get(0x8000) if hasattr(m.memory, "get") else None
    if b is None:
        try:
            b = m.memory[0x8000]
        except Exception:
            b = 0
    return {"ok": True, "result": b, "steps": 1, "err": None,
            "halted": m.halted}


MACHINES = {
    "ti85": run_ti85,
    "pyvm": run_pyvm,
    "rv32": run_rv32,
    "z80": run_z80,
    "m6502": run_m6502,
    "thumb2": run_thumb2,
    "dataflow": run_dataflow,
}

DESCRIPTIONS = {
    "ti85": "scientific expression calculator, TI syntax: "
            "sqrt(841) + 17.4^3, 10!, ncr(49,6), sin(pi/2)",
    "pyvm": "Python-subset program: define solve() and return the "
            "answer. Loops, ifs, sqrt/ln/sin/factorial/ncr builtins.",
    "rv32": "RV32I RISC-V assembly; result = signed word written to "
            "address 2048. Registers zero,t0-t6,s0-s11,a0-a7.",
    "z80": "Zilog Z80 assembly (kosarev assembler+core); result = byte "
           "at 0x8000. Registers A,F,B,C,D,E,H,L; org 0x8000 optional.",
    "m6502": "MOS 6502 assembly (py65 exact semantics); result = A "
             "register at BRK. Zero page, indexed, indirect modes.",
    "thumb2": "ARM Thumb-2 text assembly; result = r0 at program end. "
              "APSR flags, condition suffixes (adds/cmp/beq...), no IT "
              "blocks. Result convention: mov r0 with the answer.",
    "dataflow": "Dataflow compute graph (JSON): nodes with ops "
                "(const/add/sub/mul/div/mod/pow/lt/gt/mux/sqrt), "
                "readiness-driven firing, no program counter.",
}


def run(machine, code):
    fn = MACHINES.get(machine)
    if fn is None:
        return {"ok": False, "err": f"unknown machine: {machine}",
                "steps": 0, "result": None, "machine": machine}
    r = fn(code)
    r["machine"] = machine
    return r


def tool_schemas():
    """OpenAI tool schemas for every machine (model-facing)."""
    out = []
    for name, fn in MACHINES.items():
        out.append({
            "type": "function",
            "function": {
                "name": name,
                "description": "Execute code on the " + name +
                               " machine (deterministic, sandboxed). "
                               + DESCRIPTIONS[name],
                "parameters": {"type": "object",
                               "properties": {
                                   "code": {"type": "string"}},
                               "required": ["code"]},
            },
        })
    return out


def execute_tool_calls(message, max_calls=8):
    """Run every machine tool-call found in an assistant message.
    Returns (tool_result_messages, summary)."""
    results = []
    for c in message.get("tool_calls") or []:
        fn = c.get("function", {})
        name = fn.get("name")
        if name not in MACHINES:
            continue
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except Exception:
            args = {}
        code = args.get("code") or args.get("asm") or \
            args.get("expression") or ""
        r = run(name, code)
        r["tool_call_id"] = c.get("id", "")
        results.append(r)
        if len(results) >= max_calls:
            break
    msgs = [{"role": "tool", "tool_call_id": r["tool_call_id"],
             "content": json.dumps({"result": r["result"],
                                    "ok": r["ok"], "err": r["err"]})}
            for r in results]
    return msgs, results


if __name__ == "__main__":
    for m in MACHINES:
        code = {"ti85": "sqrt(841) + 17.4^3",
                "pyvm": "def solve():\n    return sum(range(11))",
                "rv32": "addi t0, zero, 47\naddi t1, zero, 13\n"
                        "add t2, t0, t1\nsw t2, 2048(x0)",
                "z80": "    org 0x8000\n    ld a, 6\n    add a, 7\n"
                       "    ld (0x8000), a\n    halt",
                "m6502": "LDA #6\nCLC\nADC #7\nBRK",
                "thumb2": "movs r0, #6\nadds r0, #7\nbx lr",
                "dataflow": json.dumps({"nodes": [
                    {"id": "a", "op": "const", "value": 6},
                    {"id": "b", "op": "const", "value": 7},
                    {"id": "s", "op": "add", "a": "a", "b": "b"}],
                    "output": "s"})}[m]
        r = run(m, code)
        print(f"{m:>5}: ok={r['ok']} result={r['result']} err={r['err']}")
