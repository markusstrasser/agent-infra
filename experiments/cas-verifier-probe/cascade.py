import json, arms, llm_arm
pairs = [json.loads(l) for l in open("pairs.jsonl")]
# deterministic-first: trust a TRUE from symbolica-or-sympy (low FP); else route to LLM
det_true=0; routed=[]; 
det = []
for p in pairs:
    sv = arms.symbolica_arm(p["reference"], p["candidate"])
    yv = arms.sympy_arm(p["reference"], p["candidate"])
    verdict = True if (sv[0] is True or yv[0] is True) else None
    det.append(verdict)
    if verdict is None:
        routed.append(p)
# LLM only on routed
lv,_ = llm_arm.run(routed)
# assemble final
ri=0; tp=fp=tn=fn=0
ridx=0
final=[]
for p,d in zip(pairs,det):
    if d is True:
        f=True
    else:
        f=bool(lv.get(ridx, False)); ridx+=1
    final.append(f)
    if p["label"] and f: tp+=1
    elif p["label"] and not f: fn+=1
    elif not p["label"] and f: fp+=1
    else: tn+=1
n=len(pairs)
print(f"\nCASCADE (det-TRUE trusted, {len(routed)}/{n} routed to LLM):")
print(f"  acc={100*(tp+tn)/n:.1f}%  FN={100*fn/250:.1f}%  FP={100*fp/250:.1f}%")
print(f"  LLM calls saved: {n-len(routed)}/{n} = {100*(n-len(routed))/n:.0f}% fewer LLM judgments")
