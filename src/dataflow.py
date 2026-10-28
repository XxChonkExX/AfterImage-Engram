"""dataflow: a deterministic static-dataflow machine (research sandbox).

Programs are compute GRAPHS, not instruction sequences: every node
fires when its inputs are ready; there is no program counter. The
model writes the graph as JSON - the natural way to express
data-driven computation deterministically.

Graph format:
  {
    "nodes": [
      {"id": "x",   "op": "const", "value": 5},
      {"id": "y",   "op": "const", "value": 7},
      {"id": "sum", "op": "add",   "a": "x", "b": "y"},
      {"id": "sq",  "op": "mul",   "a": "sum", "b": "sum"}
    ],
    "output": "sq"
  }

Ops: const(value), add(a,b), sub(a,b), mul(a,b), div(a,b), mod(a,b),
pow(a,b), neg(a), min(a,b), max(a,b), abs(a), lt/gt/le/ge/eq/ne(a,b)
(-> 0/1), mux(c,t,f) (select), sqrt(a), sum_all(inputs...) when "ins"
is a list.

Firing rule (deterministic): repeatedly evaluate every un-evaluated
node whose inputs are all ready, in node-id order per wave. If a wave
makes no progress and the output is still unknown, the graph has a
cycle or a missing input -> error.

Usage:
  python dataflow.py --selftest
  from dataflow import run_graph; run_graph(json_graph_string)
"""
import argparse
import json
import math

MAX_WAVES = 1000


def run_graph(src, max_waves=MAX_WAVES):
    try:
        g = json.loads(src) if isinstance(src, str) else src
    except Exception as e:
        return {"ok": False, "err": f"json: {e}", "steps": 0,
                "result": None}
    nodes = g.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return {"ok": False, "err": "missing nodes", "steps": 0,
                "result": None}
    out_id = g.get("output")
    if not out_id:
        return {"ok": False, "err": "missing output id", "steps": 0,
                "result": None}

    by_id = {}
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n or "op" not in n:
            return {"ok": False, "err": "bad node", "steps": 0,
                    "result": None}
        if n["id"] in by_id:
            return {"ok": False, "err": f"duplicate id {n['id']}",
                    "steps": 0, "result": None}
        by_id[n["id"]] = n

    if out_id not in by_id:
        return {"ok": False, "err": f"output {out_id} not a node",
                "steps": 0, "result": None}

    vals = {}
    waves = 0

    def inputs_of(n):
        if "ins" in n and isinstance(n["ins"], list):
            return [by_id[i] for i in n["ins"] if i in by_id]
        ins = []
        for k in ("a", "b", "c", "t", "f"):
            if k in n and n[k] in by_id:
                ins.append(by_id[n[k]])
        return ins

    def evaluate(n, args):
        op = n["op"]
        if op == "const":
            return n.get("value", 0)
        if op in BIN:
            a, b = args
            if op == "add":
                return a + b
            if op == "sub":
                return a - b
            if op == "mul":
                return a * b
            if op == "div":
                if b == 0:
                    raise ZeroDivisionError("div by zero")
                return a / b
            if op == "mod":
                if b == 0:
                    raise ZeroDivisionError("mod by zero")
                return a % b
            if op == "pow":
                if abs(b) > 256:
                    raise ValueError("exponent too large")
                return a ** b
        if op in CMP:
            a, b = args
            c = CMP[op](a, b)
            return 1 if c else 0
        if op == "neg":
            return -args[0]
        if op == "abs":
            return abs(args[0])
        if op == "sqrt":
            if args[0] < 0:
                raise ValueError("sqrt of negative")
            return math.sqrt(args[0])
        if op == "min":
            return min(args)
        if op == "max":
            return max(args)
        if op == "sum_all":
            return sum(args)
        if op == "mux":
            c, t, f = args
            return t if c else f
        raise ValueError(f"unknown op: {op}")

    CMP = {"lt": lambda a, b: a < b, "gt": lambda a, b: a > b,
           "le": lambda a, b: a <= b, "ge": lambda a, b: a >= b,
           "eq": lambda a, b: a == b, "ne": lambda a, b: a != b}
    BIN = {"add", "sub", "mul", "div", "mod", "pow"}

    try:
        while waves < max_waves and out_id not in vals:
            waves += 1
            progress = False
            for nid in sorted(by_id):
                if nid in vals:
                    continue
                n = by_id[nid]
                ins = inputs_of(n)
                if any(i["id"] not in vals for i in ins):
                    continue
                if "ins" in n and isinstance(n.get("ins"), list):
                    args = [vals[i["id"]] for i in ins]
                else:
                    args = []
                    for k in ("a", "b", "c", "t", "f"):
                        if k in n and n[k] in vals:
                            args.append(vals[n[k]])
                    for k in ("a", "b", "c", "t", "f"):
                        if k in n and n[k] not in by_id:
                            args.append(n[k])
                vals[nid] = evaluate(n, args)
                progress = True
            if not progress:
                missing = [i for i in by_id if i not in vals]
                return {"ok": False, "steps": waves,
                        "err": f"stalled (cycle or missing input near "
                               f"{missing[:3]})", "result": None}
    except (ZeroDivisionError, ValueError, TypeError, KeyError) as e:
        return {"ok": False, "err": str(e), "steps": waves, "result": None}

    return {"ok": True, "err": None, "steps": waves,
            "result": vals[out_id]}


SELFTEST = [
    ("add two consts",
     '{"nodes":[{"id":"x","op":"const","value":6},'
     '{"id":"y","op":"const","value":7},'
     '{"id":"s","op":"add","a":"x","b":"y"}],"output":"s"}', 13),
    ("diamond", '{"nodes":[{"id":"a","op":"const","value":3},'
     '{"id":"b","op":"const","value":4},'
     '{"id":"sq1","op":"mul","a":"a","b":"a"},'
     '{"id":"sq2","op":"mul","a":"b","b":"b"},'
     '{"id":"s","op":"add","a":"sq1","b":"sq2"}],"output":"s"}', 25),
    ("mux select", '{"nodes":[{"id":"c","op":"const","value":0},'
     '{"id":"t","op":"const","value":100},'
     '{"id":"f","op":"const","value":200},'
     '{"id":"m","op":"mux","c":"c","t":"t","f":"f"}],"output":"m"}', 200),
    ("compare", '{"nodes":[{"id":"a","op":"const","value":5},'
     '{"id":"b","op":"const","value":3},'
     '{"id":"c","op":"gt","a":"a","b":"b"}],"output":"c"}', 1),
    ("cycle", '{"nodes":[{"id":"a","op":"add","a":"b","b":"a"},'
     '{"id":"b","op":"const","value":1}],"output":"a"}', "CYCLE"),
    ("chain", '{"nodes":[{"id":"a","op":"const","value":2},'
     '{"id":"b","op":"pow","a":"a","b":"a"},'
     '{"id":"c","op":"neg","a":"b"}],"output":"c"}', -4),
]


def selftest():
    fails = 0
    for name, src, want in SELFTEST:
        r = run_graph(src)
        if want == "CYCLE":
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
        print(run_graph(open(a.file, encoding="utf-8").read()))
    else:
        print(__doc__)
