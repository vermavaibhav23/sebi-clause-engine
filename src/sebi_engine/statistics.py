"""Paired family-cluster bootstrap; uncertainty is not a novelty certificate."""
import random


def cluster_bootstrap(predictions, candidate, baseline, repetitions=2000, seed=20261029):
    by_mode={m:{p["id"]:p for p in predictions if p["mode"]==m} for m in [candidate,baseline]}
    left,right=by_mode[candidate],by_mode[baseline]
    if not left or left.keys()!=right.keys():
        raise ValueError("Paired comparison requires identical nonempty question sets")
    clusters={}
    for key,p in left.items():
        family=p.get("family_id")
        if not family or family!=right[key].get("family_id"):
            raise ValueError("Every pair needs the same independently assigned family ID")
        clusters.setdefault(family,[]).append(int(p["rubric_pass"])-int(right[key]["rubric_pass"]))
    observed=sum(sum(v) for v in clusters.values())/len(left)
    if len(clusters)<5:
        return {"difference":observed,"families":len(clusters),"ci95":None,
                "status":"too_few_independent_families","note":"No inferential interval reported with fewer than five families."}
    rng=random.Random(seed); names=sorted(clusters); samples=[]
    for _ in range(repetitions):
        values=[v for family in rng.choices(names,k=len(names)) for v in clusters[family]]
        samples.append(sum(values)/len(values))
    samples.sort()
    return {"difference":observed,"families":len(clusters),"ci95":[samples[int(.025*(repetitions-1))],samples[int(.975*(repetitions-1))]],
            "repetitions":repetitions,"seed":seed,"status":"exploratory_cluster_interval"}


def risk_coverage(predictions):
    """One empirical operating point per configured method; no invented confidence curve."""
    out={}
    for mode in sorted({p["mode"] for p in predictions}):
        rows=[p for p in predictions if p["mode"]==mode]
        answered=[p for p in rows if p["prediction"]["status"]!="insufficient_evidence"]
        out[mode]={"coverage":len(answered)/len(rows),
            "answered_rubric_error_rate":sum(not p["rubric_pass"] for p in answered)/len(answered) if answered else None}
    return out
