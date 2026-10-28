"""mathcheck: extract verifiable arithmetic claims from model output and
evaluate them with the TI-85.

A sweep pass returns a list of findings:
  {"expr", "claimed", "computed", "match"}

Extraction targets equalities of the form <expr> = <value> where the
left side is machine-checkable arithmetic (digits, + - * / ^ %, sqrt(),
\frac{a}{b}, \cdot, \times, parentheses). LaTeX wrappers are normalized
before parsing. Module-level API: sweep(text) -> findings list.
"""
import re

import ti85

# normalize LaTeX/typographic math into plain arithmetic
_REPLACEMENTS = [
    (r"\\cdot", "*"), (r"\\times", "*"), (r"\\div", "/"),
    (r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))"),
    (r"\\d?frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))"),
    (r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)"),
    (r"\\binom\{([^{}]+)\}\{([^{}]+)\}", r"ncr(\1, \2)"),
    (r"\\pmod\{([^{}]+)\}", r"%(\1)"),
    (r"\\%", "%"), (r'\\"', '"'),
    (r"\\left", ""), (r"\\right", ""), (r"\\,", " "), (r"\\;", " "),
    (r"\\!", ""), (r"~", " "),
]

_EXPR = r"[0-9 darinoutcsqtlgepifactombrdiu\(\)\+\-\*/\^%\.\,\/\{\}]"


def _normalize(text):
    t = text
    for pat, rep in _REPLACEMENTS:
        t = re.sub(pat, rep, t)
    # drop leftover latex commands except those ti85 knows
    t = re.sub(r"\\[a-zA-Z]+", " ", t)
    t = t.replace("{", "(").replace("}", ")")
    return t


def _iter_equalities(text):
    """Yield (expr_str, claimed_str) pairs from normalized text.

    Line-anchored: each line may hold one equality; this prevents
    cross-boundary pairing (e.g. a bare '- 2101' continuation line
    becoming a bogus expression).
    """
    t = _normalize(text)
    for line in t.splitlines():
        if "=" not in line:
            continue
        for m in re.finditer(
                r"([0-9a-zA-Z\.\s\(\)\+\-\*/\^%,\!]{3,80}?)\s*=\s*"
                r"(-?\d[\d\,]*(?:\.\d+)?)", line):
            expr = m.group(1).strip(" \t\n+,")
            # strip leading prose words (keep function names like ncr/sqrt)
            expr = re.sub(r"^(?:(?:and|so|thus|the|we|compute|first|"
                          r"therefore|then|hence|now|it|is|a|an|calculate|"
                          r"gives?|getting)\s+)+", "", expr, flags=re.I)
            # drop pure sign-prefix / bare-number junk
            if not re.search(r"[\+\-\*/\^%!]|sqrt|ncr|npr|fact|log|ln|sin|"
                             r"cos|tan|hypot|mean|gcd", expr):
                continue
            if not any(ch.isdigit() for ch in expr):
                continue
            if len(expr) < 3:
                continue
            yield expr, m.group(2).replace(",", "")


def sweep(text):
    """Evaluate every checkable equality; return findings."""
    findings = []
    seen = set()
    for expr, claimed in _iter_equalities(text):
        key = (expr, claimed)
        if key in seen:
            continue
        seen.add(key)
        computed = ti85.calculate(expr)
        if computed.startswith("ERROR"):
            # leading prose poisons the expression; retry from the first
            # digit or opening parenthesis
            stripped = expr.strip()
            for ch in ("(", "0", "1", "2", "3", "4", "5", "6", "7", "8",
                       "9"):
                p = stripped.find(ch)
                if p > 0:
                    computed = ti85.calculate(stripped[p:])
                    break
            else:
                continue
            if computed.startswith("ERROR"):
                continue
            expr = stripped[stripped.find("(") if "(" in stripped else 0:] \
                if "(" in stripped else stripped
        try:
            cv = float(computed)
            pv = float(claimed)
            match = abs(cv - pv) < 1e-6 * max(1.0, abs(pv), abs(cv))
        except ValueError:
            match = computed == claimed
        findings.append({"expr": expr, "claimed": claimed,
                         "computed": computed, "match": bool(match)})
    return findings


def report(findings, max_lines=12):
    """Human/router-readable verification report."""
    lines = []
    for f in findings:
        mark = "OK" if f["match"] else "MISMATCH"
        lines.append(f"[{mark}] {f['expr']} = {f['computed']} "
                     f"(model wrote: {f['claimed']})")
    return "\n".join(lines[:max_lines])


SELFTEST = [
    ("We compute $47^2 = 2209$ first.", 1, 0),
    ("So $2^{10} = 1025$ exactly.", 1, 1),              # wrong on purpose
    ("The probability is $\\frac{120}{1024} = 0.1171875$.", 1, 0),
    ("Thus $10! = 3628800$.", 1, 0),
    ("So $2209 \\pmod{191} = 37$.", 1, 1),              # wrong on purpose
    ("And $\\binom{10}{3} = 120$ combinations.", 1, 0),
]


def selftest():
    for text, n_min, n_bad in SELFTEST:
        f = sweep(text)
        bad = sum(1 for x in f if not x["match"])
        ok = (len(f) >= n_min and bad == n_bad)
        print(f"{'PASS' if ok else 'FAIL'} sweep({text[:40]!r}) "
              f"findings={len(f)} mismatches={bad}")
        for x in f:
            print("   ", x)


if __name__ == "__main__":
    selftest()
