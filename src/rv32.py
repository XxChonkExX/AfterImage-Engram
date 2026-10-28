"""rv32: a small deterministic RV32I emulator (safe execution sandbox).

Implements the RV32I base ISA + a tiny convention: the program's
"output" is whatever it writes to memory at OUTPUT_BASE (2048).
Execution is capped (max_steps), memory-capped, no syscalls, no host
access - safe by construction. Deterministic: same program + data +
input regs = same result.

Assembly dialect: standard RV32I text, e.g.
    addi t0, zero, 47
    addi t1, zero, 13
    add  t2, t0, t1
    sw   t2, 2048(x0)

Usage:
  python rv32.py --selftest
  python rv32.py program.s
  from rv32 import run_asm; run_asm("addi t0, zero, 6\\nsw t0, 2048(x0)")
"""
import argparse
import re

REG_NAMES = {"zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
             "t0": 5, "t1": 6, "t2": 7, "s0": 8, "fp": 8, "s1": 9,
             "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15,
             "a6": 16, "a7": 17, "s2": 18, "s3": 19, "s4": 20, "s5": 21,
             "s6": 22, "s7": 23, "s8": 24, "s9": 25, "s10": 26,
             "s11": 27, "t3": 28, "t4": 29, "t5": 30, "t6": 31}

OUTPUT_BASE = 2048
MEM_SIZE = 4096
MAX_STEPS = 20000


def _reg(tok):
    tok = tok.strip().rstrip(",")
    if tok in REG_NAMES:
        return REG_NAMES[tok]
    if tok.startswith("x") and tok[1:].isdigit():
        n = int(tok[1:])
        if 0 <= n <= 31:
            return n
    raise ValueError(f"bad register {tok!r}")


def _imm(tok):
    tok = tok.strip().rstrip(",")
    return int(tok, 0)


def parse_asm(src):
    """Parse text assembly into [(mnemonic, operands)]; labels become
    instruction indices for branches/jumps."""
    labels = {}
    instrs = []
    for raw in src.splitlines():
        line = raw.split("#")[0].strip()
        while True:
            m = re.match(r"^([A-Za-z_][\w\.]*):\s*(.*)$", line)
            if not m:
                break
            labels[m.group(1)] = len(instrs)
            line = m.group(2).strip()
        if not line:
            continue
        parts = line.split(None, 1)
        mn = parts[0].lower()
        ops = [o.strip() for o in parts[1].split(",")] if len(parts) > 1 \
            else []
        instrs.append((mn, ops))
    out = []
    for mn, ops in instrs:
        if mn in ("beq", "bne", "blt", "bge", "bltu", "bgeu") and ops and \
                ops[-1] in labels:
            ops = ops[:-1] + [str(labels[ops[-1]])]
        if mn in ("jal", "j") and ops and ops[-1] in labels:
            ops = ops[:-1] + [str(labels[ops[-1]])]
        out.append((mn, ops))
    return out


def run_asm(src, a0=0, a1=0, a2=0, max_steps=MAX_STEPS):
    """Execute assembly; returns dict(ok, result, steps, err)."""
    instrs = parse_asm(src)
    regs = [0] * 32
    regs[10] = a0 & 0xFFFFFFFF
    regs[11] = a1 & 0xFFFFFFFF
    regs[12] = a2 & 0xFFFFFFFF
    mem = bytearray(MEM_SIZE)
    pc = 0
    steps = 0
    err = None

    def S(v):
        return v - 0x100000000 if v & 0x80000000 else v

    def R(i):
        return _reg(ops[i])

    def I(i):
        return _imm(ops[i])

    def MR(i):
        o = ops[i]
        if "(" in o:
            off_s, reg_s = o.split("(", 1)
            off = int(off_s.strip()) if off_s.strip() else 0
            return (_reg(reg_s.rstrip(")")) + off) & 0xFFFFFFFF
        raise ValueError(f"expected off(reg), got {o!r}")

    while pc < len(instrs):
        if steps >= max_steps:
            err = "step limit exceeded"
            break
        mn, ops = instrs[pc]
        steps += 1
        npc = pc + 1
        try:
            if mn in ("add", "sub", "and", "or", "xor", "sll", "srl",
                      "sra", "slt", "sltu"):
                a, b = regs[R(1)], regs[R(2)]
                v = {"add": a + b, "sub": a - b, "and": a & b,
                     "or": a | b, "xor": a ^ b,
                     "sll": a << (b & 31),
                     "srl": (a & 0xFFFFFFFF) >> (b & 31),
                     "sra": (S(a) >> (b & 31)),
                     "slt": 1 if S(a) < S(b) else 0,
                     "sltu": 1 if a < b else 0}[mn] & 0xFFFFFFFF
                regs[R(0)] = v
            elif mn in ("addi", "andi", "ori", "xori", "slli", "srli",
                        "srai", "slti", "sltiu"):
                a, b = regs[R(1)], I(2)
                v = {"addi": a + b, "andi": a & b, "ori": a | b,
                     "xori": a ^ b, "slli": a << (b & 31),
                     "srli": (a & 0xFFFFFFFF) >> (b & 31),
                     "srai": S(a) >> (b & 31),
                     "slti": 1 if S(a) < b else 0,
                     "sltiu": 1 if a < (b & 0xFFFFFFFF) else 0}[mn]
                regs[R(0)] = v & 0xFFFFFFFF
            elif mn == "lw":
                addr = MR(1)
                if addr + 4 > MEM_SIZE:
                    raise ValueError(f"memory read OOB: {addr}")
                regs[R(0)] = int.from_bytes(mem[addr:addr + 4], "little")
            elif mn == "sw":
                addr = MR(1)
                if addr + 4 > MEM_SIZE:
                    raise ValueError(f"memory write OOB: {addr}")
                mem[addr:addr + 4] = (regs[R(0)] & 0xFFFFFFFF) \
                    .to_bytes(4, "little")
            elif mn in ("beq", "bne", "blt", "bge", "bltu", "bgeu"):
                a, b = regs[R(0)], regs[R(1)]
                take = {"beq": a == b, "bne": a != b,
                        "blt": S(a) < S(b), "bge": S(a) >= S(b),
                        "bltu": a < b, "bgeu": a >= b}[mn]
                if take:
                    npc = I(2)
            elif mn == "jal":
                if len(ops) == 1:
                    regs[1] = pc + 1
                    npc = I(0)
                else:
                    regs[R(0)] = pc + 1
                    npc = I(1)
            elif mn == "jalr":
                regs[R(0)] = pc + 1
                npc = (regs[R(1)] + I(2)) & 0xFFFFFFFF
            elif mn == "j":
                npc = I(0)
            elif mn == "li":
                regs[R(0)] = I(1) & 0xFFFFFFFF
            elif mn == "mv":
                regs[R(0)] = regs[R(1)]
            elif mn == "nop":
                pass
            elif mn == "ecall":
                npc = len(instrs)
            else:
                raise ValueError(f"unsupported instruction: {mn}")
        except Exception as e:
            err = f"{type(e).__name__} at pc={pc} ({mn}): {e}"
            break
        regs[0] = 0
        pc = npc
    result = int.from_bytes(mem[OUTPUT_BASE:OUTPUT_BASE + 4], "little")
    return {"ok": err is None, "err": err, "steps": steps,
            "result": S(result), "result_u32": result}


SELFTEST = [
    ("sum", "addi t0, zero, 47\naddi t1, zero, 13\nadd t2, t0, t1\n"
            "sw t2, 2048(x0)", 60),
    ("countdown", "addi t0, zero, 5\nloop:\naddi t0, t0, -1\n"
                  "bne t0, zero, loop\nsw t0, 2048(x0)", 0),
    ("fib10", "addi t0, zero, 10\naddi t1, zero, 0\naddi t2, zero, 1\n"
              "loop:\nbeq t0, zero, done\nadd t3, t1, t2\nmv t1, t2\n"
              "mv t2, t3\naddi t0, t0, -1\njal loop\ndone:\n"
              "sw t1, 2048(x0)", 55),
    ("load-store", "addi t0, zero, 1234\nsw t0, 2048(x0)\n"
                   "lw t1, 2048(x0)\naddi t1, t1, 1\nsw t1, 2048(x0)",
     1235),
    ("shift-xor", "addi t0, zero, 5\nslli t1, t0, 4\naddi t0, zero, 3\n"
                  "xor t2, t1, t0\nsw t2, 2048(x0)", 83),
]


def selftest():
    fails = 0
    for name, asm, want in SELFTEST:
        r = run_asm(asm, max_steps=5000)
        ok = r["ok"] and r["result"] == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: result={r['result']} "
              f"(want {want}) steps={r['steps']} err={r['err']}")
    print("fails:", fails)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.file:
        print(run_asm(open(a.file, encoding="utf-8").read()))
    else:
        print(__doc__)
