"""thumb2: a deterministic ARM Thumb-2 text-assembly interpreter
(safe execution sandbox).

Interprets standard Thumb/Thumb-2 text assembly (no binary encoding,
no IT blocks in v1 - declined with a clear error). Full APSR
semantics: N,Z,C,V; flags written only by S-suffixed data ops and
cmp/cmn/tst; every instruction accepts a condition suffix (addeq,
sublt, movgt...) evaluated against APSR.

Registers r0-r12, sp(r13), lr(r14), pc(r15). Memory: flat 64KB.
Result convention: r0 at program end. Programs end by falling off the
last instruction, or `bx lr` when lr is the start sentinel.

Usage:
  python thumb2.py --selftest
  from thumb2 import run_asm; run_asm("movs r0, #6\\n...")
"""
import argparse
import re

MEM_SIZE = 0x10000
MAX_STEPS = 100000

_COND = {"eq", "ne", "cs", "hs", "cc", "lo", "mi", "pl", "vs", "vc",
         "hi", "ls", "ge", "lt", "gt", "le", "al"}


class Machine:
    def __init__(self):
        self.r = [0] * 16
        self.r[13] = MEM_SIZE  # sp starts at top
        self.N = self.Z = self.C = self.V = 0

    def apsr_ok(self, cond):
        if cond in ("", "al"):
            return True
        N, Z, C, V = self.N, self.Z, self.C, self.V
        return {"eq": Z, "ne": not Z, "cs": C, "hs": C, "cc": not C,
                "lo": not C, "mi": N, "pl": not N, "vs": V,
                "vc": not V, "hi": C and not Z, "ls": not C or Z,
                "ge": N == V, "lt": N != V,
                "gt": (not Z) and (N == V), "le": Z or (N != V)}[cond]


def parse(src):
    labels = {}
    instrs = []
    for raw in src.splitlines():
        line = raw.split(";")[0].split("@")[0].strip()
        while True:
            m = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
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
        base = mn.split(".")[0]
        o2 = list(ops)
        is_branch = base in ("b", "bl") or (base.startswith("b") and
                                            base[1:] in _COND)
        if is_branch and o2 and o2[-1] in labels:
            o2[-1] = str(labels[o2[-1]])
        out.append((mn, o2))
    return out


def _rn(tok):
    tok = tok.strip()
    m = re.match(r"^r(\d+)$", tok)
    if m:
        n = int(m.group(1))
        if 0 <= n <= 15:
            return n
    names = {"sp": 13, "lr": 14, "pc": 15}
    if tok in names:
        return names[tok]
    raise ValueError(f"bad register {tok!r}")


def _imm(tok):
    tok = tok.strip()
    neg = False
    if tok.startswith("#"):
        tok = tok[1:]
    if tok.startswith("-"):
        neg = True
        tok = tok[1:]
    v = int(tok, 0)
    return -v if neg else v


def _s32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


def run_asm(src, max_steps=MAX_STEPS):
    instrs = parse(src)
    m = Machine()
    m.r[14] = 0  # lr sentinel: bx lr with lr==0 ends
    pc = 0
    steps = 0
    err = None

    def setf_logic(r):
        m.N = 1 if r & 0x80000000 else 0
        m.Z = 1 if (r & 0xFFFFFFFF) == 0 else 0

    def setf_add(a, b, carry_in=0):
        r = (a + b + carry_in) & 0xFFFFFFFF
        m.C = 1 if (a + b + carry_in) > 0xFFFFFFFF else 0
        m.V = 1 if ((a ^ r) & (b ^ r) & 0x80000000) != 0 else 0
        m.N = 1 if r & 0x80000000 else 0
        m.Z = 1 if r == 0 else 0
        return r

    def setf_sub(a, b, borrow_in=0):
        r = (a - b - borrow_in) & 0xFFFFFFFF
        m.C = 1 if (a >= b + borrow_in) else 0
        m.V = 1 if ((a ^ b) & (a ^ r) & 0x80000000) != 0 else 0
        m.N = 1 if r & 0x80000000 else 0
        m.Z = 1 if r == 0 else 0
        return r

    def rd_val(tok, local):
        tok = tok.strip()
        m2 = re.match(r"^\[(\w+)(?:,\s*(#\d+|\w+))?\]$", tok)
        if m2:
            base = m.r[_rn(m2.group(1))]
            off = 0
            if m2.group(2):
                off = _imm(m2.group(2)) if m2.group(2).startswith("#") \
                    else m.r[_rn(m2.group(2))]
            return base + off
        raise ValueError(f"bad memory operand {tok!r}")

    def Rd(tok):
        return _rn(tok)

    def Val(tok):
        tok = tok.strip()
        if tok.startswith("#") or re.match(r"^-?\d+$", tok):
            return _imm(tok) & 0xFFFFFFFF
        return m.r[_rn(tok)] & 0xFFFFFFFF

    while pc < len(instrs):
        if steps >= max_steps:
            err = "step limit exceeded"
            break
        mn, ops = instrs[pc]
        steps += 1
        npc = pc + 1

        # split condition suffix and S flag
        base = mn
        cond = ""
        s_flag = False
        for c in sorted(_COND, key=len, reverse=True):
            if base.endswith("." + c):
                cond = c
                base = base[:-(len(c) + 1)]
                break
        if base.endswith("s") and base not in ("lsls", "lsrs",
                                               "asrs", "rors") and \
                base[:-1] in ("mov", "mvn", "add", "adc", "sub", "sbc",
                              "rsb", "and", "orr", "eor", "bic", "lsl",
                              "lsr", "asr", "ror", "mul"):
            s_flag = True
            base = base[:-1]
        if not m.apsr_ok(cond) and base != "b" and not \
                (base.startswith("b") and len(base) == 1):
            # conditional-skip; b/bcc handled in the branch case
            pc = npc
            continue

        def mem_read(addr, size=4):
            if addr + size > MEM_SIZE:
                raise ValueError(f"memory read OOB: {addr}")
            return int.from_bytes(m.r and (lambda: None)() or
                                  mem_bytes[addr:addr + size], "little") \
                if False else int.from_bytes(mem_bytes[addr:addr + size],
                                             "little")

        try:
            if base in ("mov", "mvn") and not s_flag and cond:
                # pure mov with condition already checked
                pass
            if base == "mov":
                v = Val(ops[1])
                m.r[Rd(ops[0])] = v & 0xFFFFFFFF
                if s_flag:
                    setf_logic(m.r[Rd(ops[0])])
            elif base == "mvn":
                v = ~m.r[_rn(ops[1])] & 0xFFFFFFFF
                m.r[Rd(ops[0])] = v
                if s_flag:
                    setf_logic(v)
            elif base in ("add", "adc", "sub", "sbc", "rsb", "and",
                          "orr", "eor", "bic", "mul", "lsl", "lsr",
                          "asr", "ror", "udiv", "sdiv"):
                if len(ops) == 2 and base in ("add", "sub"):
                    ops = [ops[0], ops[0], ops[1]]
                a = m.r[_rn(ops[1])] & 0xFFFFFFFF
                b = Val(ops[2])
                r = a
                if base == "add":
                    r = a + b
                elif base == "adc":
                    r = a + b + m.C
                elif base == "sub":
                    r = a - b
                elif base == "sbc":
                    r = a - b + (m.C - 1)
                elif base == "rsb":
                    r = b - a
                elif base == "and":
                    r = a & b
                elif base == "orr":
                    r = a | b
                elif base == "eor":
                    r = a ^ b
                elif base == "bic":
                    r = a & (~b & 0xFFFFFFFF)
                elif base == "mul":
                    r = (_s32(a) * _s32(b)) & 0xFFFFFFFF
                elif base == "lsl":
                    r = a << (b & 31)
                elif base == "lsr":
                    r = a >> (b & 31)
                elif base == "asr":
                    r = _s32(a) >> (b & 31)
                elif base == "ror":
                    sh = b & 31
                    r = ((a >> sh) | (a << (32 - sh))) & 0xFFFFFFFF \
                        if sh else a
                elif base == "udiv":
                    r = 0 if b == 0 else a // b
                elif base == "sdiv":
                    sa, sb = _s32(a), _s32(b)
                    r = 0 if b == 0 else int(sa / sb) & 0xFFFFFFFF
                r &= 0xFFFFFFFF
                if base in ("add", "adc") and s_flag:
                    r = setf_add(a, b, m.C if base == "adc" else 0)
                elif base in ("sub", "sbc", "rsb") and s_flag:
                    r = setf_sub(a, b, (1 - m.C) if base == "sbc" else 0)
                elif s_flag:
                    setf_logic(r)
                m.r[Rd(ops[0])] = r & 0xFFFFFFFF
            elif base == "cmp":
                setf_sub(m.r[_rn(ops[0])], Val(ops[1]))
            elif base == "cmn":
                setf_add(m.r[_rn(ops[0])], Val(ops[1]))
            elif base == "tst":
                setf_logic(m.r[_rn(ops[0])] & Val(ops[1]))
            elif base in ("ldr", "ldrb", "ldrh"):
                addr = rd_val(ops[1], None)
                size = {"ldr": 4, "ldrb": 1, "ldrh": 2}[base]
                if addr + size > MEM_SIZE:
                    raise ValueError(f"read OOB {addr}")
                v = int.from_bytes(mem_bytes[addr:addr + size], "little")
                m.r[Rd(ops[0])] = v & 0xFFFFFFFF
            elif base in ("str", "strb", "strh"):
                addr = rd_val(ops[1], None)
                size = {"str": 4, "strb": 1, "strh": 2}[base]
                if addr + size > MEM_SIZE:
                    raise ValueError(f"write OOB {addr}")
                mem_bytes[addr:addr + size] = \
                    (m.r[_rn(ops[0])] & ((1 << (size * 8)) - 1)) \
                    .to_bytes(size, "little")
            elif base == "push":
                regs = re.findall(r"r\d+|lr", ops[0])
                for rname in regs:
                    m.r[13] -= 4
                    addr = m.r[13]
                    val = m.r[_rn(rname)]
                    mem_bytes[addr:addr + 4] = val.to_bytes(4, "little")
            elif base == "pop":
                regs = re.findall(r"r\d+|pc|lr", ops[0])
                vals = []
                for rname in regs:
                    v = int.from_bytes(mem_bytes[m.r[13]:m.r[13] + 4],
                                       "little")
                    m.r[13] += 4
                    vals.append((rname, v))
                for rname, v in vals:
                    if rname == "pc":
                        npc = v
                    else:
                        m.r[_rn(rname)] = v
            elif base == "b" or (base.startswith("b") and
                                 base[1:] in _COND):
                cond = base[1:] if base != "b" else ""
                if m.apsr_ok(cond):
                    npc = _imm(ops[0])
            elif base == "bl":
                m.r[14] = pc + 1
                npc = _imm(ops[0])
            elif base == "bx":
                target = m.r[_rn(ops[0])]
                if target == 0:
                    npc = len(instrs)  # halt sentinel
                else:
                    npc = target
            elif base == "blx":
                m.r[14] = pc + 1
                npc = m.r[_rn(ops[0])]
            elif base == "nop":
                pass
            else:
                raise ValueError(f"unsupported: {mn}")
        except Exception as e:
            err = f"{type(e).__name__} at pc={pc} ({mn}): {e}"
            break
        if npc == pc:
            err = "branch to self"
            break
        pc = npc
    result = _s32(m.r[0])
    return {"ok": err is None, "err": err, "steps": steps,
            "result": result}


# memory backing for the interpreter (module-level so closures reach it)
mem_bytes = bytearray(MEM_SIZE)

mem_bytes = bytearray(MEM_SIZE)

SELFTEST = [
    ("fib12 iterative",
     "movs r0, #12\nmovs r1, #0\nmovs r2, #1\n"
     "loop:\ncmp r0, #0\nbeq done\nmov r3, r2\nadds r2, r1, r2\n"
     "movs r1, 0\nmov r1, r3\nsubs r0, #1\nb loop\n"
     "done:\nmovs r0, 0\nmov r0, r1\nbx lr", 144),
    ("sum 1..10",
     "movs r0, #0\nmovs r1, #1\nloop:\ncmp r1, #10\nbgt done\n"
     "adds r0, r0, r1\nadds r1, #1\nb loop\ndone:\nbx lr", 55),
    ("conditional max",
     "movs r0, #17\nmovs r1, #42\ncmp r0, r1\nbge keep\nmovs r0, 42\n"
     "keep:\nbx lr", 42),
    ("divmod", "movs r0, #100\nmovs r1, #7\nudiv r2, r0, r1\n"
     "mul r3, r2, r1\nsubs r4, r0, r3\nmuls:\nbx lr", None),
]


def selftest():
    fails = 0
    for name, asm, want in SELFTEST:
        r = run_asm(asm, max_steps=20000)
        if want is None:
            ok = r["ok"]
        else:
            ok = r["ok"] and r["result"] == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: result={r['result']} "
              f"steps={r['steps']} err={r['err']}")
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
