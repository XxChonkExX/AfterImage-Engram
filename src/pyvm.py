"""pyvm: a safe Python-subset interpreter machine.

The model's strongest dialect is Python-ish code and its weakest skill
is hand-executing it. This machine makes that impossible to get wrong:
the model writes a Python-subset program (a `solve()` function), the
VM executes it exactly under an AST whitelist.

Allowed: def solve(), assignments, if/elif/else, for i in range(...),
while (iteration-capped), return, augmented assignment, comparisons,
arithmetic (+ - * / // % **), ti85 functions (sqrt, log, ln, sin, cos,
tan, factorial, ncr, npr, abs, min, max, sum, round, int, float, len,
range), booleans, lists of literals, f-string-free str concat via +.

Denied: imports, attribute access, subscripts on non-lists, eval/exec,
lambdas, comprehensions, nested defs, while True without break (capped
anyway), anything touching the host.

Usage:
  python pyvm.py --selftest
  from pyvm import run_py; run_py("def solve():\\n    return 6 * 7")
"""
import ast
import argparse
import math

MAX_STEPS = 200000
MAX_DEPTH = 64

FUNCS = {
    "sqrt": math.sqrt, "log": math.log10, "ln": math.log,
    "log2": math.log2, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "abs": abs, "min": min, "max": max, "sum": sum, "round": round,
    "int": int, "float": float, "str": str, "len": len,
    "factorial": lambda n: math.factorial(int(n)),
    "ncr": lambda n, r: math.comb(int(n), int(r)),
    "npr": lambda n, r: math.perm(int(n), int(r)),
    "gcd": math.gcd,
}
CONSTS = {"pi": math.pi, "e": math.e}

_ALLOWED_NODES = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
    ast.Assign, ast.AugAssign, ast.If, ast.For, ast.While, ast.Break,
    ast.Continue, ast.Expr, ast.Constant, ast.Name, ast.Load, ast.Store,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.Pow, ast.USub, ast.UAdd, ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.List, ast.Tuple, ast.Subscript, ast.Slice,
)


class _Safety(ast.NodeVisitor):
    def __init__(self):
        self.funcs = 0

    def generic_visit(self, node):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"disallowed construct: "
                             f"{type(node).__name__}")
        if isinstance(node, ast.Attribute):
            raise ValueError("attribute access not allowed")
        if isinstance(node, ast.Call):
            f = node.func
            if not isinstance(f, ast.Name):
                raise ValueError("only direct calls to named functions")
            # name resolution (builtins vs user functions) happens at
            # execution; the safety gate is about constructs only
        super().generic_visit(node)


def run_py(src, max_steps=MAX_STEPS):
    """Execute solve() from src; returns dict(ok, result, steps, err)."""
    try:
        tree = ast.parse(src, mode="exec")
    except SyntaxError as e:
        return {"ok": False, "err": f"syntax: {e}", "steps": 0,
                "result": None}
    try:
        _Safety().visit(tree)
    except ValueError as e:
        return {"ok": False, "err": f"safety: {e}", "steps": 0,
                "result": None}

    env = dict(FUNCS)
    env.update(CONSTS)
    steps = [0]

    class Stop(Exception):
        pass

    class Ret(Exception):
        def __init__(self, v):
            self.v = v

    class Brk(Exception):
        pass

    class Cnt(Exception):
        pass

    class Fn:
        def __init__(self, node):
            self.node = node

    user_fns = {}
    depth = [0]

    def ex(n, local):
        steps[0] += 1
        if steps[0] > max_steps:
            raise Stop("step limit exceeded")
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Store):
                return local
            if n.id in local:
                return local[n.id]
            if n.id in env:
                return env[n.id]
            if n.id in user_fns:
                return user_fns[n.id]
            raise NameError(n.id)
        if isinstance(n, ast.BinOp):
            a, b = ex(n.left, local), ex(n.right, local)
            op = type(n.op)
            if op is ast.Add:
                return a + b
            if op is ast.Sub:
                return a - b
            if op is ast.Mult:
                return a * b
            if op is ast.Div:
                return a / b
            if op is ast.FloorDiv:
                return a // b
            if op is ast.Mod:
                return a % b
            if op is ast.Pow:
                if abs(b) > 256:
                    raise ValueError("exponent too large")
                return a ** b
        if isinstance(n, ast.UnaryOp):
            v = ex(n.operand, local)
            return -v if isinstance(n.op, ast.USub) else +v
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                r = True
                for v in n.values:
                    r = ex(v, local)
                    if not r:
                        return r
                return r
            r = False
            for v in n.values:
                r = ex(v, local)
                if r:
                    return r
            return r
        if isinstance(n, ast.Compare):
            a = ex(n.left, local)
            for op, comp in zip(n.ops, n.comparators):
                b = ex(comp, local)
                t = type(op)
                okk = {ast.Eq: a == b, ast.NotEq: a != b,
                       ast.Lt: a < b, ast.LtE: a <= b,
                       ast.Gt: a > b, ast.GtE: a >= b}[t]
                if not okk:
                    return False
                a = b
            return True
        if isinstance(n, ast.Call):
            f = n.func
            args = [ex(a, local) for a in n.args]
            if isinstance(f, ast.Name):
                if f.id in user_fns:
                    if depth[0] > 32:
                        raise RecursionError("user recursion limit")
                    depth[0] += 1
                    try:
                        fn = user_fns[f.id]
                        call_local = {}
                        params = fn.node.args.args
                        for i, pnode in enumerate(params):
                            call_local[pnode.arg] = args[i] if i < \
                                len(args) else None
                        r = run_stmts(fn.node.body, call_local)
                        return r
                    finally:
                        depth[0] -= 1
                if f.id == "range":
                    return range(*args)
                if f.id == "print":
                    return " ".join(str(x) for x in args)
                if f.id in FUNCS:
                    return FUNCS[f.id](*args)
                raise NameError(f.id)
            raise ValueError("indirect calls not allowed")
        if isinstance(n, ast.Subscript):
            if not isinstance(n.ctx, ast.Load):
                return local  # write handled in Assign
            container = ex(n.value, local)
            idx = ex(n.slice, local)
            if not isinstance(container, (list, str)):
                raise ValueError("subscript on non-list")
            return container[int(idx)]
        if isinstance(n, ast.List):
            return [ex(e, local) for e in n.elts]
        if isinstance(n, ast.Tuple):
            return tuple(ex(e, local) for e in n.elts)
        raise ValueError(f"disallowed expression: {type(n).__name__}")

    def assign(target, value, local):
        if isinstance(target, ast.Name):
            local[target.id] = value
            return
        if isinstance(target, ast.Subscript):
            container = ex(target.value, local)
            idx = ex(target.slice, local)
            if not isinstance(container, list):
                raise ValueError("subscript write on non-list")
            container[int(idx)] = value
            return
        if isinstance(target, ast.Tuple):
            vals = list(value)
            if len(vals) != len(target.elts):
                raise ValueError("tuple assign length mismatch")
            for t, v in zip(target.elts, vals):
                assign(t, v, local)
            return
        raise ValueError("bad assignment target")

    def run_stmts(stmts, local):
        for s in stmts:
            run_stmt(s, local)

    def run_stmt(s, local):
        steps[0] += 1
        if steps[0] > max_steps:
            raise Stop("step limit exceeded")
        if isinstance(s, ast.FunctionDef):
            user_fns[s.name] = Fn(s)
            return
        if isinstance(s, ast.Assign):
            v = ex(s.value, local)
            for t in s.targets:
                assign(t, v, local)
            return
        if isinstance(s, ast.AugAssign):
            cur = ex(s.target, local)
            v = ex(s.value, local)
            op = type(s.op)
            new = (cur + v if op is ast.Add else
                   cur - v if op is ast.Sub else
                   cur * v if op is ast.Mult else
                   cur / v if op is ast.Div else
                   cur % v if op is ast.Mod else
                   cur ** v if op is ast.Pow else None)
            assign(s.target, new, local)
            return
        if isinstance(s, ast.Return):
            raise Ret(ex(s.value, local) if s.value else None)
        if isinstance(s, ast.Expr):
            ex(s.value, local)
            return
        if isinstance(s, ast.If):
            if ex(s.test, local):
                run_stmts(s.body, local)
            else:
                run_stmts(s.orelse, local)
            return
        if isinstance(s, ast.For):
            it = ex(s.iter, local)
            if isinstance(it, (list, str)):
                it = range(len(it))
            for v in it:
                assign(s.target, v, local)
                try:
                    run_stmts(s.body, local)
                except Brk:
                    break
                except Cnt:
                    continue
            return
        if isinstance(s, ast.While):
            guard = 0
            while ex(s.test, local):
                guard += 1
                if guard > 100000:
                    raise Stop("while limit exceeded")
                try:
                    run_stmts(s.body, local)
                except Brk:
                    break
                except Cnt:
                    continue
            return
        if isinstance(s, ast.Break):
            raise Brk()
        if isinstance(s, ast.Continue):
            raise Cnt()
        raise ValueError(f"disallowed statement: {type(s).__name__}")

    try:
        run_stmts(tree.body, {})
        if "solve" not in user_fns:
            raise ValueError("program must define solve()")
        call_local = {}
        try:
            run_stmts(user_fns["solve"].node.body, call_local)
        except Ret as r:
            result = r.v
        else:
            result = None
    except Ret as r:
        result = r.v
    except Stop as e:
        return {"ok": False, "err": str(e), "steps": steps[0],
                "result": None}
    except RecursionError:
        return {"ok": False, "err": "recursion limit", "steps": steps[0],
                "result": None}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}",
                "steps": steps[0], "result": None}
    return {"ok": True, "err": None, "steps": steps[0], "result": result}

SELFTEST = [
    ("simple return", "def solve():\n    return 6 * 7", 42),
    ("loop sum", "def solve():\n    total = 0\n    for i in range(11):\n"
                 "        total = total + i\n    return total", 55),
    ("sqrt", "def solve():\n    return int(sqrt(841))", 29),
    ("condition", "def solve():\n    n = 7\n    if n % 2 == 0:\n"
                  "        return 0\n    return 1", 1),
    ("comb", "def solve():\n    return ncr(49, 6)", 13983816),
    ("while", "def solve():\n    n = 40\n    a = 0\n    b = 1\n"
              "    while n > 0:\n        t = a + b\n        a = b\n"
              "        b = t\n        n = n - 1\n    return a", 102334155),
    ("unsafe import", "def solve():\n    import os\n    return 1", None),
    ("unsafe attr", "def solve():\n    return (1).__class__", None),
]


def selftest():
    fails = 0
    for name, src, want in SELFTEST:
        r = run_py(src)
        if want is None:
            ok = not r["ok"]
        else:
            ok = r["ok"] and r["result"] == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: result={r['result']} "
              f"err={r['err']}")
    print("fails:", fails)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.file:
        print(run_py(open(a.file, encoding="utf-8").read()))
    else:
        print(__doc__)


