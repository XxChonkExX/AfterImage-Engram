"""m6502: MOS 6502 research toolkit (safe execution sandbox).

Built on py65 (MIT) - exact flag and addressing semantics.

Components:
  assemble(text)  -> bytes  (table auto-derived from py65's own decode
                             map, so every opcode/py is correct)
  run(text)       -> execute at 0x1000 with a step cap; BRK ends;
                     result = A register at halt
  disassemble(bytes or text) -> text

Dialect: standard 6502 assembly. LDA #$05, STA $0200, LDA $0200,X,
JSR $F00D, BEQ label (labels auto-resolved), implied ops bare.
Result conventions: end with BRK; read A (and memory) afterwards.
"""
import re

from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

BASE = 0x1000
MAX_STEPS = 50000

# build the assembler table by inverting py65's decode map
_MPU = MPU()
ASM_TABLE = {}  # (mnemonic, addressing) -> opcode
for byte in range(256):
    dis, addr = _MPU.disassemble[byte]
    mn = dis.split()[0].upper() if dis else ""
    key = (mn, addr)
    if key not in ASM_TABLE:
        ASM_TABLE[key] = byte


def _words(text):
    out = []
    for raw in text.splitlines():
        line = raw.split(";")[0].strip()
        while True:
            m = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
            if not m:
                break
            out.append(("LABEL", m.group(1), None))
            line = m.group(2).strip()
        if not line:
            continue
        parts = line.split(None, 1)
        mn = parts[0].upper()
        rest = parts[1].strip() if len(parts) > 1 else ""
        out.append((mn, rest, None))
    return out


def _addr_mode(operand, labels, pc):
    """Returns (addressing, value_bytes, resolve_later_label)."""
    if operand == "":
        return "imp", [], None
    if operand.upper() == "A":
        return "acc", [], None
    if operand.startswith("#"):
        v = _value(operand[1:], labels)
        return "imm", [v & 0xFF], None
    m = re.match(r"^\((\S+),\s*X\)$", operand, re.I)
    if m:
        return "inx", [], m.group(1)
    m = re.match(r"^\((\S+)\)\s*,\s*Y$", operand, re.I)
    if m:
        return "iny", [], m.group(1)
    m = re.match(r"^\((\S+)\)$", operand, re.I)
    if m:
        return "ind", [], m.group(1)
    m = re.match(r"^(\S+),\s*X$", operand, re.I)
    if m:
        v = _value(m.group(1), labels)
        mode = "zpx" if v is not None and v <= 0xFF else "abx"
        return mode, ([] if v is None else
                      [v & 0xFF] if mode == "zpx" else
                      [v & 0xFF, (v >> 8) & 0xFF]), \
            None if v is not None else m.group(1)
    m = re.match(r"^(\S+),\s*Y$", operand, re.I)
    if m:
        v = _value(m.group(1), labels)
        mode = "zpy" if v is not None and v <= 0xFF else "aby"
        return mode, ([] if v is None else
                      [v & 0xFF] if mode == "zpy" else
                      [v & 0xFF, (v >> 8) & 0xFF]), \
            None if v is not None else m.group(1)
    v = _value(operand, labels)
    if v is None:
        # branch or absolute label - decide at fixup
        return "label", [], operand
    if v <= 0xFF:
        return "zpg", [v], None
    return "abs", [v & 0xFF, (v >> 8) & 0xFF], None


def _is_label(tok):
    return bool(re.match(r"^[A-Za-z_]", tok or "")) and \
        not tok.startswith("$") and not tok.startswith("%")


def _value(tok, labels):
    tok = tok.strip()
    if _is_label(tok):
        return labels.get(tok)
    try:
        return int(tok.replace("$", "0x").replace("%", "0b"), 0)
    except ValueError:
        return None


def _mode_key(mn, addressing):
    if addressing == "label":
        # branches take a relative byte; JMP takes absolute
        addressing = "rel" if (mn, "rel") in ASM_TABLE else "abs"
    k = (mn, addressing)
    if k in ASM_TABLE:
        return k
    # branches: Bcc share 'rel'
    if addressing == "rel":
        return (mn, "rel")
    # implied ops sometimes listed as 'imp' or 'acc'
    if (mn, "imp") in ASM_TABLE:
        return (mn, "imp")
    return k


def assemble(text):
    """6502 text assembly -> bytes loaded at BASE (returns base, bytes)."""
    lines = _words(text)
    # pass 1: label addresses (instruction sizes from the table)
    labels = {}
    pc = BASE
    sized = []
    for mn, rest, _ in lines:
        if mn == "LABEL":
            labels[rest] = pc
            sized.append((mn, rest))
            continue
        if mn in ("BNE", "BEQ", "BCS", "BCC", "BMI", "BPL", "BVS",
                  "BVC") and _is_label(rest.split(",")[0]):
            mode, valbytes, label = "label", [], rest
        else:
            mode, valbytes, label = _addr_mode(rest, labels, pc)
        key = _mode_key(mn, mode)
        if key not in ASM_TABLE:
            raise ValueError(f"unsupported: {mn} {rest} ({mode})")
        op = ASM_TABLE[key]
        size = 1 + len(valbytes)
        sized.append((mn, rest, (op, valbytes, size, mode, label)))
        pc += size
    # pass 2: emit with label fixups
    out = bytearray()
    pc = BASE
    for item in sized:
        if item[0] == "LABEL":
            continue
        mn, rest, (op, valbytes, size, mode, label) = item
        out.append(op)
        if label is not None:
            target = labels.get(label)
            if target is None:
                raise ValueError(f"unknown label: {label}")
            if mode == "label":
                if mn in ("BNE", "BEQ", "BCS", "BCC", "BMI", "BPL",
                          "BVS", "BVC"):
                    off = target - (pc + 2)
                    if not -128 <= off <= 127:
                        raise ValueError(f"branch out of range: {label}")
                    out.append(off & 0xFF)
                else:
                    out.append(target & 0xFF)
                    out.append((target >> 8) & 0xFF)
            continue
        for b in valbytes:
            out.append(b & 0xFF)
        pc += size
    return BASE, bytes(out)


def run(text, max_steps=MAX_STEPS):
    """Assemble + execute; result = A at BRK/RTS end."""
    base, image = assemble(text)
    m = MPU()
    for i, b in enumerate(image):
        m.memory[base + i] = b
    m.pc = base
    steps = 0
    err = None
    try:
        while steps < max_steps:
            if m.pc == 0xFFFF or m.memory[m.pc] == 0x00:  # BRK ends
                m.p |= 0x10
                break
            m.step()
            steps += 1
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    else:
        if steps >= max_steps:
            err = "step limit exceeded"
    return {"ok": err is None, "err": err, "steps": steps,
            "result": m.a, "a": m.a, "x": m.x, "y": m.y}


def disassemble(data, base=BASE):
    """bytes -> text asm (py65 disassembler)."""
    m = MPU()
    for i, b in enumerate(data):
        m.memory[base + i] = b
    d = Disassembler(m)
    lines = []
    pc = base
    while pc < base + len(data):
        length, text = d.instruction_at(pc)
        lines.append(f"{pc:04X}  {text}")
        pc += max(1, length)
    return "\n".join(lines)


SELFTEST = [
    ("sum", "LDA #$05\nCLC\nADC #$08\nBRK", 13),
    ("loop sum 1..10", "LDA #$00\nLDX #$0A\nLOOP: CLC\nADC #1\n"
                       "DEX\nBNE LOOP2\nBRK\nLOOP2: CLC\nADC X_DUMMY\nBRK", None),
]


def selftest():
    # 1. straight-line sum
    r = run("LDA #$05\nCLC\nADC #$08\nBRK")
    print(("PASS" if r["ok"] and r["a"] == 13 else "FAIL"), "sum:", r)
    # 2. loop: count 10 iterations via X
    r = run("LDA #$00\nLDX #$0A\nLOOP: CLC\nADC #1\nDEX\nBNE LOOP\nBRK")
    print(("PASS" if r["ok"] and r["a"] == 10 else "FAIL"), "loop:", r)
    # 3. zero page + indexed
    r = run("LDA #$07\nSTA $30\nLDX #$00\nLDA $30,X\nBRK")
    print(("PASS" if r["ok"] and r["a"] == 7 else "FAIL"), "zpx:", r)
    # 4. disassemble round trip
    base, image = assemble("LDA #$05\nSTA $0200\nBRK")
    d = disassemble(image, base)
    print(("PASS" if "LDA #$05" in d and "STA $0200" in d else "FAIL"),
          "disasm:", d.replace("\n", " | "))


if __name__ == "__main__":
    selftest()

