import json, arms
pairs = [json.loads(l) for l in open("pairs.jsonl")]
print("=== symbolica FALSE POSITIVES (label=False but arm said equivalent) ===")
n=0
for p in pairs:
    if p["label"]: continue
    v,cov,_ = arms.symbolica_arm(p["reference"], p["candidate"])
    if cov and v is True:
        n+=1
        print(f"[{p['kind']}] ref={p['reference'][:35]!r} cand={p['candidate'][:35]!r}")
print("total symbolica FP:", n)
