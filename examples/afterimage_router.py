"""afterimage_router: the standard engram sidecar for any model server.

One config-driven process that turns any OpenAI-compatible llama.cpp
server into a grounded, arithmetic-verifying endpoint:

  POST /v1/chat/completions  - passthrough
  POST /v1/engram/chat       - reference injection (retrieval grounding)
  POST /v1/calc/chat         - abacus ledger: natural answer, then every
                               arithmetic claim swept with the TI-85,
                               machine-verified fact ledger fed back for
                               one repair round
  POST /v1/verify/chat       - sweep + repair only (no injection)
  POST /v1/engram/search     - raw retrieval
  GET  /engram/stats         - index stats

Usage:
  python afterimage_router.py --records my_engram.jsonl \
      --upstream http://127.0.0.1:8012 --port 8014

The engram is optional (--records omitted = verification-only mode).
Tools: ti85 calculator, mathcheck sweep, rv32 emulator (riscv tool is
advertised to the model when --riscv-tool is passed and the caller
sends a tools array).
"""
import argparse
import json
import os
import sys

import requests
from flask import Flask, request, jsonify

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, r"C:\Users\mikeh\Documents\New OpenCode Project\AfterImage-Engram\src")
from afterimage_engine_v2 import Retriever  # noqa: E402
import mathcheck  # noqa: E402
import ti85  # noqa: E402
import machines  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8014)
ap.add_argument("--upstream", default="http://127.0.0.1:8012")
ap.add_argument("--records", default=None,
                help="engram records jsonl; omit for verify-only mode")
ap.add_argument("--k", type=int, default=3)
ap.add_argument("--max-repairs", type=int, default=1)
a = ap.parse_args()

RET = None
if a.records and os.path.exists(a.records):
    RECORDS = [json.loads(l) for l in open(a.records, encoding="utf-8")
               if l.strip()]
    RET = Retriever(RECORDS)
    print(f"[engram] {len(RECORDS)} records, {len(RET.units)} units",
          flush=True)
else:
    RECORDS = []
    print("[engram] disabled (verify-only mode)", flush=True)

app = Flask(__name__)


def last_user(messages):
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def upstream(body):
    r = requests.post(a.upstream + "/v1/chat/completions", json=body,
                      timeout=900)
    return r.json(), r.status_code


def inject(messages, q):
    """Engram injection; returns (messages, units). No-op if disabled."""
    if RET is None:
        return messages, 0
    ctx, n = RET.search(q, k=a.k)
    block = ("[Reference material retrieved for this request; use it if "
             "relevant, ignore it if not:]\n" + ctx[:4000] +
             "\n[End reference material.]\n\n")
    out, done = [], False
    for m in messages:
        if m.get("role") == "user" and not done:
            out.append({"role": "user", "content": block + m["content"]})
            done = True
        else:
            out.append(m)
    return out, n


@app.post("/v1/chat/completions")
def passthrough():
    out, code = upstream(request.get_json(force=True))
    return jsonify(out), code


@app.post("/v1/engram/chat")
def engram_chat():
    if RET is None:
        return jsonify({"error": "engram disabled (no --records)"}), 400
    body = request.get_json(force=True)
    msgs = body.get("messages", [])
    q = last_user(msgs)
    body["messages"], n = inject(msgs, q)
    out, code = upstream(body)
    if code == 200 and isinstance(out, dict):
        out["engram"] = {"query": q[:120], "units": n}
    return jsonify(out), code


def verify_repair(body):
    """Sweep the answer's arithmetic; repair from the fact ledger."""
    out, code = upstream(body)
    answer = (out.get("choices") or [{}])[0].get("message", {}).get(
        "content", "") if code == 200 else ""
    findings = mathcheck.sweep(answer) if answer else []
    bad = [f for f in findings if not f["match"]]
    repaired = False
    rounds = 0
    while bad and rounds < a.max_repairs:
        rounds += 1
        ledger_lines = []
        for f in findings:
            if f["match"]:
                ledger_lines.append(f"{f['expr']} = {f['computed']} "
                                    "[verified]")
            else:
                ledger_lines.append(f"{f['expr']} = {f['computed']} "
                                    f"[CORRECTED - model wrote "
                                    f"{f['claimed']}]")
        ledger = ("\n\n[MACHINE-VERIFIED FACT LEDGER - use ONLY these "
                  "values for arithmetic in your final answer:]\n" +
                  "\n".join(ledger_lines) +
                  "\n[End ledger. Restate the solution and final answer "
                  "using these verified values.]")
        head = ("Arithmetic verification of your answer found errors:\n"
                + mathcheck.report(bad) + "\n\n") if bad else ""
        msgs = body.get("messages", []) + [
            {"role": "assistant", "content": answer},
            {"role": "user", "content": head + ledger}]
        out2, code2 = upstream({**body, "messages": msgs})
        answer2 = (out2.get("choices") or [{}])[0].get("message", {}).get(
            "content", "") if code2 == 200 else ""
        if not answer2.strip():
            break
        findings2 = mathcheck.sweep(answer2)
        bad2 = [f for f in findings2 if not f["match"]]
        if len(bad2) <= len(bad):
            out, answer, findings, bad = out2, answer2, findings2, bad2
            repaired = True
        else:
            break
    meta = {"checked": len(findings), "mismatches": len(bad),
            "repaired": repaired, "rounds": rounds,
            "findings": findings[:12]}
    return out, code, meta


@app.post("/v1/verify/chat")
def verify_chat():
    body = request.get_json(force=True)
    out, code, meta = verify_repair(body)
    if isinstance(out, dict):
        out["verify"] = meta
    return jsonify(out), code


@app.post("/v1/calc/chat")
def calc_chat():
    """Engram injection + verify-and-repair in one call."""
    if RET is None:
        return jsonify({"error": "engram disabled (no --records)"}), 400
    body = request.get_json(force=True)
    msgs = body.get("messages", [])
    q = last_user(msgs)
    body["messages"], n = inject(msgs, q)
    out, code, meta = verify_repair(body)
    if isinstance(out, dict):
        meta["engram_units"] = n
        meta["query"] = q[:120]
        out["agent"] = meta
    return jsonify(out), code


@app.post("/v1/engram/search")
def engram_search():
    if RET is None:
        return jsonify({"error": "engram disabled"}), 400
    body = request.get_json(force=True)
    ctx, n = RET.search(body.get("query", ""), k=int(body.get("k", a.k)))
    return jsonify({"context": ctx, "units": n})



@app.post("/v1/machines/chat")
def machines_chat():
    """Agentic machine loop: the model gets the hybrid machine family
    (ti85/pyvm/rv32/z80) as tools; the router executes each call on the
    real machine and feeds results back until the final answer."""
    body = request.get_json(force=True)
    msgs = body.get("messages", [])
    q = last_user(msgs)
    if RET is not None:
        body["messages"], n = inject(msgs, q)
    tools = list(body.get("tools") or [])
    have = {t.get("function", {}).get("name") for t in tools}
    for t in machines.tool_schemas():
        if t["function"]["name"] not in have:
            tools.append(t)
    body["tools"] = tools

    trace = []
    for iteration in range(6):
        out, code = upstream(body)
        choice = (out.get("choices") or [{}])[0]
        calls = (choice.get("message") or {}).get("tool_calls") or []
        machine_calls = [c for c in calls
                         if c.get("function", {}).get("name")
                         in machines.MACHINES]
        if not machine_calls:
            break
        msg = choice["message"]
        new_msgs = list(body["messages"]) + [
            {"role": "assistant", "content": msg.get("content") or "",
             "tool_calls": calls}]
        for c in machine_calls:
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except Exception:
                args = {}
            code_txt = args.get("code") or args.get("asm") or \
                args.get("expression") or ""
            r = machines.run(c["function"]["name"], code_txt)
            trace.append({"machine": c["function"]["name"],
                          "code": code_txt[:200], "result": r["result"],
                          "ok": r["ok"], "err": r["err"]})
            new_msgs.append({"role": "tool",
                             "tool_call_id": c.get("id", ""),
                             "content": json.dumps(
                                 {"result": r["result"], "ok": r["ok"],
                                  "err": r["err"]})})
        body["messages"] = new_msgs
    out["machines"] = {"query": q[:120], "calls": trace}
    return jsonify(out), 200

@app.get("/engram/stats")
def stats():
    return jsonify({"records": len(RECORDS),
                    "units": len(RET.units) if RET else 0,
                    "upstream": a.upstream})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=a.port, threaded=True)



