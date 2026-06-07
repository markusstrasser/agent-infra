"""Run all four verifier arms over the 500 labeled pairs; emit metrics + decision table."""
import json
from collections import defaultdict
import arms, llm_arm

ALGEBRAIC = {"expression", "numeric"}  # the CAS's home turf


def load():
    return [json.loads(l) for l in open("pairs.jsonl")]


def run_det(pairs, fn):
    out = []
    for p in pairs:
        v, cov, sec = fn(p["reference"], p["candidate"])
        out.append((v, cov, sec))
    return out


def metrics(pairs, results):
    """results: list of (verdict|None, covered, sec) aligned with pairs."""
    m = defaultdict(lambda: dict(fn=0, fp=0, tp=0, tn=0, abstain=0, n=0, sec=0.0,
                                 cov=0, fn_seen=0, fp_seen=0))
    for p, (v, cov, sec) in zip(pairs, results):
        for bucket in ("ALL", "ALG" if p["kind"] in ALGEBRAIC else "NONALG", p["kind"]):
            d = m[bucket]
            d["n"] += 1; d["sec"] += sec
            if v is None or not cov:
                d["abstain"] += 1
                continue
            d["cov"] += 1
            if p["label"]:           # truly equivalent
                d["fn_seen"] += 1
                if v: d["tp"] += 1
                else: d["fn"] += 1
            else:                    # truly not equivalent
                d["fp_seen"] += 1
                if v: d["fp"] += 1
                else: d["tn"] += 1
    return m


def rate(num, den):
    return f"{100*num/den:.1f}%" if den else "—"


def fmt(name, m):
    d = m["ALL"]
    cov = rate(d["cov"], d["n"])
    fn = rate(d["fn"], d["fn_seen"])
    fp = rate(d["fp"], d["fp_seen"])
    acc = rate(d["tp"] + d["tn"], d["cov"])
    msec = 1000 * d["sec"] / d["n"] if d["n"] else 0
    return f"| {name} | {cov} | {fn} | {fp} | {acc} | {msec:.2f} |"


def main():
    pairs = load()
    print(f"loaded {len(pairs)} pairs")

    print("running regex..."); reg = run_det(pairs, arms.regex_arm)
    print("running sympy..."); syp = run_det(pairs, arms.sympy_arm)
    print("running symbolica..."); sym = run_det(pairs, arms.symbolica_arm)
    print("running llm (gpt-5.5)...")
    lv, lsec = llm_arm.run(pairs)
    llm = [(lv.get(i), i in lv, lsec) for i in range(len(pairs))]

    armset = {"regex": reg, "sympy": syp, "symbolica": sym, "llm(gpt-5.5)": llm}
    M = {name: metrics(pairs, res) for name, res in armset.items()}

    lines = []
    lines.append("## Results — overall (500 pairs, 250 equivalent / 250 not)\n")
    lines.append("| arm | coverage | FN rate | FP rate | acc(covered) | ms/pair |")
    lines.append("|-----|----------|---------|---------|--------------|---------|")
    for name in ("regex", "sympy", "symbolica", "llm(gpt-5.5)"):
        lines.append(fmt(name, M[name]))

    # algebraic slice — the H2 crux
    lines.append("\n## Algebraic slice only (expression+numeric, the CAS home turf)\n")
    lines.append("| arm | coverage | FN rate | FP rate | acc(covered) |")
    lines.append("|-----|----------|---------|---------|--------------|")
    for name in ("regex", "sympy", "symbolica", "llm(gpt-5.5)"):
        d = M[name]["ALG"]
        lines.append(f"| {name} | {rate(d['cov'],d['n'])} | {rate(d['fn'],d['fn_seen'])} "
                     f"| {rate(d['fp'],d['fp_seen'])} | {rate(d['tp']+d['tn'],d['cov'])} |")

    # per-kind FN rate for sympy vs symbolica
    lines.append("\n## sympy vs symbolica by answer-kind (coverage | FN | FP)\n")
    lines.append("| kind | n | sympy cov | sympy FN | sympy FP | symbolica cov | symbolica FN | symbolica FP |")
    lines.append("|------|---|-----------|----------|----------|---------------|--------------|--------------|")
    kinds = sorted({p["kind"] for p in pairs})
    for k in kinds:
        ds, dy = M["sympy"][k], M["symbolica"][k]
        lines.append(f"| {k} | {ds['n']} | {rate(ds['cov'],ds['n'])} | {rate(ds['fn'],ds['fn_seen'])} "
                     f"| {rate(ds['fp'],ds['fp_seen'])} | {rate(dy['cov'],dy['n'])} "
                     f"| {rate(dy['fn'],dy['fn_seen'])} | {rate(dy['fp'],dy['fp_seen'])} |")

    out = "\n".join(lines)
    print("\n" + out)
    with open("results.md", "w") as f:
        f.write(out + "\n")
    with open("results.json", "w") as f:
        json.dump({n: {b: dict(v) for b, v in M[n].items()} for n in M}, f, indent=2)
    print("\nwrote results.md, results.json")


if __name__ == "__main__":
    main()
