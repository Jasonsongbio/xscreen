"""Bootstrap split-half 稳定性验证

按 source_pmid 把 evidence 随机分两半（零 API 成本，复用 evidence_db.json），
分别 score，比较两个 top-K 的重合度。高重合 = xscreen 抽取的是真信号，
不是随机噪声。

跑 10 次（不同 seed）取平均，给出 stability 的置信区间。

用法：
    python tools/bootstrap_stability.py
"""
import json
import random
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_config


def score_evidence_subset(evidence_list: list[dict], config: dict,
                          min_studies_override: int | None = None) -> list[tuple]:
    """复现 score.py 的排名逻辑（ortholog_mult 省略——统一因子不影响排名）。

    返回 [(candidate, total_score, study_count), ...] 降序。
    """
    weights = config.get("extraction", {}).get("weights", {})
    w_level = config["scoring"]["weight_level"]
    w_conv = config["scoring"]["weight_convergence"]
    min_studies = min_studies_override if min_studies_override is not None else config["scoring"]["min_studies"]

    by_cand: dict[str, list[dict]] = defaultdict(list)
    for ev in evidence_list:
        by_cand[ev["core_name"]].append(ev)

    if not by_cand:
        return []

    study_counts = {c: len({e["source_pmid"] for e in evs}) for c, evs in by_cand.items()}
    max_studies = max(study_counts.values())

    primary_raw = {
        c: sum(weights.get(e["evidence_level"], 0) for e in evs
               if e["evidence_level"] != "review_mention")
        for c, evs in by_cand.items()
    }
    max_primary = max(primary_raw.values(), default=0.0)
    if max_primary > 0:
        max_level = max_primary
    else:
        all_raw = {c: sum(weights.get(e["evidence_level"], 0) for e in evs)
                   for c, evs in by_cand.items()}
        max_level = max(all_raw.values()) if all_raw else 1.0

    results = []
    for cand, evs in by_cand.items():
        level_raw = sum(weights.get(e["evidence_level"], 0) for e in evs)
        sc = study_counts[cand]
        convergence = sc / max_studies if max_studies > 0 else 0.0
        level_norm = level_raw / max_level if max_level > 0 else 0.0
        total = w_level * level_norm + w_conv * convergence
        if sc >= min_studies:
            results.append((cand, total, sc))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def one_split(evidence: list[dict], pmids: list[str], seed: int,
              config: dict, min_studies_override: int | None = None) -> dict:
    """单次 split-half，返回两个子集的 ranked list。"""
    random.seed(seed)
    shuffled = pmids.copy()
    random.shuffle(shuffled)
    h = len(shuffled) // 2
    set_a = set(shuffled[:h])

    ev_a = [e for e in evidence if e["source_pmid"] in set_a]
    ev_b = [e for e in evidence if e["source_pmid"] not in set_a]

    ranked_a = score_evidence_subset(ev_a, config, min_studies_override)
    ranked_b = score_evidence_subset(ev_b, config, min_studies_override)
    return {"ranked_a": ranked_a, "ranked_b": ranked_b,
            "n_pmids_a": h, "n_pmids_b": len(shuffled) - h,
            "n_ev_a": len(ev_a), "n_ev_b": len(ev_b)}


def main() -> int:
    config_path = PROJECT_ROOT / "cases/locust_sih/config_unbiased.yaml"
    config = load_config(str(config_path))

    db = json.loads(
        (PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json")
        .read_text(encoding="utf-8")
    )
    evidence = db["evidence"]
    pmids = sorted({e["source_pmid"] for e in evidence})

    print("=" * 70)
    print("Bootstrap Split-Half 稳定性验证")
    print("=" * 70)
    print(f"总 evidence: {len(evidence)}")
    print(f"总 PMID: {len(pmids)}")
    print(f"config min_studies = {config['scoring']['min_studies']}")

    # === 单次 split 详情（seed=42）===
    print(f"\n--- 单次 split（seed=42）---")
    r = one_split(evidence, pmids, 42, config)
    print(f"  组 A: {r['n_pmids_a']} PMID, {r['n_ev_a']} evidence, {len(r['ranked_a'])} 候选过 filter")
    print(f"  组 B: {r['n_pmids_b']} PMID, {r['n_ev_b']} evidence, {len(r['ranked_b'])} 候选过 filter")

    for K in (10, 20, 30):
        top_a = {c for c, _, _ in r["ranked_a"][:K]}
        top_b = {c for c, _, _ in r["ranked_b"][:K]}
        overlap = top_a & top_b
        jaccard = len(overlap) / len(top_a | top_b) if (top_a | top_b) else 0
        print(f"  Top-{K}: 重合 {len(overlap)}/{K}, Jaccard={jaccard:.3f}")

    print(f"\n  组 A Top-15: {[c for c,_,_ in r['ranked_a'][:15]]}")
    print(f"  组 B Top-15: {[c for c,_,_ in r['ranked_b'][:15]]}")

    # === 10 次 bootstrap ===
    print(f"\n--- 10 次 Bootstrap（seed 0-9）---")
    overlaps = {10: [], 20: [], 30: []}
    jaccards = {10: [], 20: [], 30: []}
    for seed in range(10):
        rr = one_split(evidence, pmids, seed, config)
        for K in (10, 20, 30):
            ta = {c for c, _, _ in rr["ranked_a"][:K]}
            tb = {c for c, _, _ in rr["ranked_b"][:K]}
            overlaps[K].append(len(ta & tb))
            union = ta | tb
            jaccards[K].append(len(ta & tb) / len(union) if union else 0)

    print(f"\n{'K':<6} {'重合 mean':<12} {'重合 range':<14} {'Jaccard mean':<14} {'stability %'}")
    print("-" * 60)
    for K in (10, 20, 30):
        o = overlaps[K]
        j = jaccards[K]
        omean = sum(o) / len(o)
        orange = f"{min(o)}-{max(o)}"
        jmean = sum(j) / len(j)
        stab = omean / K * 100
        print(f"{K:<6} {omean:<12.1f} {orange:<14} {jmean:<14.3f} {stab:.1f}%")

    # === min_studies=1 对照（split 后每半 studies 减半，min_studies=2 可能过严）===
    print(f"\n--- 对照：min_studies=1（更宽松 filter）---")
    overlaps1 = {10: [], 20: [], 30: []}
    for seed in range(10):
        rr = one_split(evidence, pmids, seed, config, min_studies_override=1)
        for K in (10, 20, 30):
            ta = {c for c, _, _ in rr["ranked_a"][:K]}
            tb = {c for c, _, _ in rr["ranked_b"][:K]}
            overlaps1[K].append(len(ta & tb))
    print(f"{'K':<6} {'重合 mean':<12} {'重合 range':<14} {'stability %'}")
    print("-" * 45)
    for K in (10, 20, 30):
        o = overlaps1[K]
        print(f"{K:<6} {sum(o)/len(o):<12.1f} {min(o)}-{max(o):<14} {sum(o)/len(o)/K*100:.1f}%")

    # 全量 top-30 作参考
    full_ranked = score_evidence_subset(evidence, config)
    print(f"\n=== 全量 ranked（参考）Top-15 ===")
    for i, (c, s, sc) in enumerate(full_ranked[:15], 1):
        print(f"  #{i:<3} {c:<20} score={s:.3f} studies={sc}")

    # 保存
    out_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/bootstrap_stability.json"
    out = {
        "description": "Bootstrap split-half stability: 10 random 50/50 splits of PMID set",
        "n_pmids": len(pmids),
        "n_evidence": len(evidence),
        "min_studies_config": config["scoring"]["min_studies"],
        "results_min_studies_config": {
            str(K): {"overlap_mean": sum(overlaps[K])/len(overlaps[K]),
                      "overlap_range": [min(overlaps[K]), max(overlaps[K])],
                      "jaccard_mean": sum(jaccards[K])/len(jaccards[K]),
                      "stability_pct": sum(overlaps[K])/len(overlaps[K])/K*100}
            for K in (10, 20, 30)
        },
        "results_min_studies_1": {
            str(K): {"overlap_mean": sum(overlaps1[K])/len(overlaps1[K]),
                      "stability_pct": sum(overlaps1[K])/len(overlaps1[K])/K*100}
            for K in (10, 20, 30)
        },
        "full_top30": [{"candidate": c, "score": s, "studies": sc}
                       for c, s, sc in full_ranked[:30]],
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ 结果保存到 {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
