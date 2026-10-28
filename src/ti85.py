"""TI-85-class scientific calculator: safe expression evaluation.

AST-whitelist evaluator - no attribute access, no names outside the
provided namespace, no calls except whitelisted functions. Supports the
TI-85's everyday scientific set: trig + inverses (radians and degrees),
logs, roots, powers, factorial, combinatorics, hypot, and basic stats.

Usage:
  python ti85.py "sqrt(841) + 17.4^3"
  python ti85.py --selftest
"""
import argparse
import ast
import math
import re
import statistics


def _fact(n):
    n = int(n)
    if n < 0 or n > 5000:
        raise ValueError("factorial out of range")
    return math.factorial(n)


def _ncr(n, r):
    return math.comb(int(n), int(r))


def _npr(n, r):
    return math.perm(int(n), int(r))


FUNCS = {
    # trig (radians)
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    # trig (degrees)
    "sind": lambda x: math.sin(math.radians(x)),
    "cosd": lambda x: math.cos(math.radians(x)),
    "tand": lambda x: math.tan(math.radians(x)),
    "asind": lambda x: math.degrees(math.asin(x)),
    "acosd": lambda x: math.degrees(math.acos(x)),
    "atand": lambda x: math.degrees(math.atan(x)),
    # logs and roots
    "log": math.log10, "ln": math.log, "log2": math.log2,
    "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "exp": math.exp,
    "abs": abs,
    # combinatorics
    "factorial": _fact, "fact": _fact, "ncr": _ncr, "npr": _npr,
    "comb": _ncr, "perm": _npr,
    # misc
    "hypot": math.hypot, "round": round, "floor": math.floor,
    "ceil": math.ceil, "gcd": math.gcd, "deg": math.degrees,
    "rad": math.radians,
    # stats (n-argument)
    "mean": lambda *a: statistics.fmean(a),
    "median": lambda *a: statistics.median(a),
    "stdev": lambda *a: statistics.stdev(a),
    "variance": lambda *a: statistics.variance(a),
    "sum": lambda *a: sum(a),
    "min": lambda *a: min(a), "max": lambda *a: max(a),
}

CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau,
          "phi": (1 + 5 ** 0.5) / 2}


class _Eval(ast.NodeVisitor):
    def __init__(self):
        self.depth = 0

    def visit(self, node):
        if self.depth > 40:
            raise ValueError("expression too deep")
        return super().visit(node)

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)) and not isinstance(
                node.value, bool):
            return node.value
        raise ValueError(f"constant not allowed: {node.value!r}")

    def visit_Name(self, node):
        if node.id in CONSTS:
            return CONSTS[node.id]
        raise ValueError(f"unknown name: {node.id}")

    def visit_BinOp(self, node):
        l, r = self.visit(node.left), self.visit(node.right)
        op = type(node.op)
        if op is ast.Add:
            return l + r
        if op is ast.Sub:
            return l - r
        if op is ast.Mult:
            return l * r
        if op is ast.Div:
            return l / r
        if op is ast.Pow:
            if abs(r) > 1000:
                raise ValueError("exponent too large")
            return l ** r
        if op is ast.Mod:
            return l % r
        if op is ast.FloorDiv:
            return l // r
        raise ValueError(f"operator not allowed: {op.__name__}")

    def visit_UnaryOp(self, node):
        v = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return v
        raise ValueError("unary op not allowed")

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS:
            raise ValueError("function not allowed")
        args = [self.visit(a) for a in node.args]
        if node.keywords:
            raise ValueError("keywords not allowed")
        return FUNCS[node.func.id](*args)

    def generic_visit(self, node):
        raise ValueError(f"syntax not allowed: {type(node).__name__}")


def calculate(expression: str) -> str:
    """Evaluate a scientific-calculator expression safely."""
    expr = expression.strip().rstrip("=")
    expr = expr.replace("^", "**")  # TI-85 power syntax
    expr = re.sub(r"\b(\d+)!", r"fact(\1)", expr)  # postfix factorial
    try:
        tree = ast.parse(expr, mode="eval")
        v = _Eval().visit(tree)
        if isinstance(v, float):
            if abs(v - round(v)) < 1e-12 and abs(v) < 1e15:
                return str(int(round(v)))
            return f"{v:.10g}"
        return str(v)
    except ZeroDivisionError:
        return "ERROR: division by zero"
    except Exception as e:
        return f"ERROR: {e}"


SELFTEST = [
    ("sqrt(841) + 17.4^3", None),          # smoke: mixed ops parse
    ("2+2", "4"),
    ("2^10", "1024"),
    ("10!", "3628800"),
    ("ncr(49, 6)", "13983816"),
    ("sin(pi/2)", "1"),
    ("cosd(60)", "0.5"),
    ("log(1000)", "3"),
    ("mean(2, 4, 9)", "5"),
    ("hypot(3, 4)", "5"),
    ("sqrt(-1)", "ERROR"),
    ("__import__('os')", "ERROR"),
    ("(lambda: 1)()", "ERROR"),
    ("().__class__", "ERROR"),
]


def selftest():
    for expr, want in SELFTEST:
        got = calculate(expr)
        try:
            if want is None:
                ok = not got.startswith("ERROR")
            elif want.startswith("ERROR"):
                ok = got.startswith("ERROR")
            else:
                ok = got == want or abs(float(got) - float(want)) < 1e-6 * max(
                    1, abs(float(want)))
        except (ValueError, AttributeError):
            ok = False
        print(f"{'PASS' if ok else 'FAIL'} {expr!r} -> {got}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("expression", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.expression:
        print(calculate(" ".join(a.expression)))
    else:
        print(__doc__)
