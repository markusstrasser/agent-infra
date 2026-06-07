"""Fetch HardVerify-Math via HF datasets-server (no full download) -> pairs.jsonl.

Each source row yields two labeled pairs:
  (ground_truth, fn_output) -> label=True  (actually equivalent; the false-negative trap)
  (ground_truth, tn_output) -> label=False (actually wrong; the false-positive trap)
"""
import json, urllib.request, time

DS = "zhangchenxu/HardVerify-Math"
BASE = "https://datasets-server.huggingface.co/rows"


def fetch_rows():
    rows, offset = [], 0
    while True:
        url = f"{BASE}?dataset={DS}&config=default&split=train&offset={offset}&length=100"
        with urllib.request.urlopen(url) as r:
            d = json.load(r)
        batch = d.get("rows", [])
        if not batch:
            break
        rows.extend(x["row"] for x in batch)
        offset += len(batch)
        if offset >= d.get("num_rows_total", 0):
            break
        time.sleep(0.3)
    return rows


def classify(gt: str) -> str:
    """Coarse answer-type bucket from the ground-truth string."""
    g = gt.strip().strip("$").strip()
    low = g.lower()
    if any(t in low for t in ("\\begin{pmatrix}", "\\begin{matrix}", "\\begin{bmatrix}")):
        return "matrix"
    if g.count("(") >= 2 and "," in g and ")" in g:  # set/list of tuples
        return "set_or_tuple"
    if g.startswith("{") or (g.count(",") >= 1 and "(" not in g and "=" not in g and any(c.isdigit() for c in g)):
        return "set_or_list"
    if any(t in g for t in ("\\in", "[", "]")) and ("," in g):
        return "interval"
    if "=" in g:  # equation / functional answer e.g. f(x)=2x
        return "equation_or_function"
    if any(c.isalpha() for c in g.replace("pi", "").replace("sqrt", "").replace("frac", "")):
        return "expression"
    return "numeric"


def main():
    rows = fetch_rows()
    out = []
    for r in rows:
        gt = (r.get("ground_truth") or "").strip()
        kind = classify(gt)
        for field, label in (("fn_output", True), ("tn_output", False)):
            cand = (r.get(field) or "").strip()
            if not cand:
                continue
            out.append({
                "id": r["id"], "source": r.get("source", ""), "kind": kind,
                "reference": gt, "candidate": cand, "label": label, "trap": field,
            })
    with open("pairs.jsonl", "w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    # quick summary
    from collections import Counter
    print(f"rows={len(rows)} pairs={len(out)}")
    print("by kind:", dict(Counter(o["kind"] for o in out)))
    print("by label:", dict(Counter(o["label"] for o in out)))


if __name__ == "__main__":
    main()
