"""Biased vs Unbiased corpus 对比（论文 Figure 2 基础）

对比 NPF 论文引用的 48 篇 corpus（output_real）vs PubMed 无偏 1349 篇
corpus（output_unbiased）的候选排名变化，量化 confirmation bias。

核心问题：NPF 在 biased corpus #1 是循环论证；在 unbiased corpus 仍 #1
才是真正的发现能力证明。

用法：
    python tools/corpus_bias_compare.py
"""
import sys
import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_scores(db_path: str) -> dict[str, dict]:
    """加载 evidence_db.json 的 candidates 部分 → {candidate: {rank, score, studies, ...}}。

    report.py write_json 输出的格式：
        {"candidates": [CandidateScore.__dict__...], "evidence": [...]}
    """
    data = json.load(open(db_path, encoding="utf-8"))
    # report.py write_json 的 candidates 字段是 dict（含 ortholog dict / None）
    cands = data.get("candidates", [])
    # 按总分降序排序（写 json 时已排，但保险起见重排）
    cands_sorted = sorted(cands, key=lambda c: c.get("total_score", 0), reverse=True)
    result = {}
    for rank, c in enumerate(cands_sorted, 1):
        result[c["candidate"]] = {
            "rank": rank,
            "score": c.get("total_score", 0),
            "studies": c.get("study_count", 0),
            "evidence_count": c.get("evidence_count", 0),
            "evidence_levels": c.get("evidence_levels", {}),
        }
    return result


def main():
    biased_db = PROJECT_ROOT / "cases/locust_sih/output_real/evidence_db.json"
    unbiased_db = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"

    if not biased_db.exists():
        print(f"ERROR: biased corpus db 不存在: {biased_db}")
        print("先跑 biased corpus pipeline (config_real.yaml)")
        sys.exit(1)
    if not unbiased_db.exists():
        print(f"ERROR: unbiased corpus db 不存在: {unbiased_db}")
        print("先跑 tools/score_unbiased.py")
        sys.exit(1)

    biased = load_scores(str(biased_db))
    unbiased = load_scores(str(unbiased_db))

    print("=" * 80)
    print("Corpus Bias 对比（Biased 48 篇 vs Unbiased 1349 篇）")
    print("=" * 80)
    print(f"Biased corpus 候选数: {len(biased)}")
    print(f"Unbiased corpus 候选数: {len(unbiased)}")

    # 所有候选并集
    all_cands = set(biased) | set(unbiased)
    only_biased = set(biased) - set(unbiased)
    only_unbiased = set(unbiased) - set(biased)
    both = set(biased) & set(unbiased)

    print(f"\n=== 候选重叠 ===")
    print(f"两 corpus 共有: {len(both)}")
    print(f"仅 biased: {len(only_biased)}")
    print(f"仅 unbiased（新发现）: {len(only_unbiased)}")

    # 排名变化表（两 corpus 都有的候选）
    print(f"\n=== 排名变化（共有候选，按 unbiased 排名）===")
    print(f"{'Candidate':<25} {'Biased':<10} {'Unbiased':<10} {'Δ':<8} {'方向'}")
    print("-" * 70)
    common_sorted = sorted(both, key=lambda c: unbiased[c]["rank"])
    for cand in common_sorted[:25]:
        b_rank = biased[cand]["rank"]
        u_rank = unbiased[cand]["rank"]
        delta = b_rank - u_rank  # 正 = unbiased 排名更靠前（上升）
        if delta > 0:
            arrow = f"↑{delta}"
        elif delta < 0:
            arrow = f"↓{abs(delta)}"
        else:
            arrow = "="
        print(f"{cand:<25} #{b_rank:<8} #{u_rank:<8} {delta:<+8} {arrow}")

    # 关键候选检验
    print(f"\n=== 关键候选 confirmation bias 检验 ===")
    key_cands = ["NPF", "AKH", "sNPF", "octopamine", "dopamine", "insulin",
                 "DH44", "allatostatin", "allatotropin", "tachykinin"]
    for kc in key_cands:
        # 模糊匹配（NPF 匹配 NPF/NPF1a/NPF2 等）
        b_matches = [c for c in biased if kc.lower() in c.lower()]
        u_matches = [c for c in unbiased if kc.lower() in c.lower()]
        for c in b_matches[:1] if b_matches else []:
            b_rank = biased[c]["rank"]
            if c in unbiased:
                u_rank = unbiased[c]["rank"]
                verdict = "独立浮现 ✓" if u_rank <= 5 else ("仍靠前" if u_rank <= 15 else "排名下滑")
                print(f"  {c:<20} biased #{b_rank} → unbiased #{u_rank}  {verdict}")
            else:
                print(f"  {c:<20} biased #{b_rank} → unbiased 未进榜（可能被 min_studies 过滤）")

    # 仅在 unbiased 浮上来的新候选（论文的"新发现"卖点）
    print(f"\n=== Unbiased corpus 独有候选（新发现，top 15）===")
    only_u_sorted = sorted(only_unbiased, key=lambda c: unbiased[c]["rank"])
    for c in only_u_sorted[:15]:
        u = unbiased[c]
        print(f"  #{u['rank']:<4} {c:<25} (studies={u['studies']}, evidence={u['evidence_count']})")

    # 保存对比结果
    out_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/corpus_bias_compare.json"
    compare_data = {
        "biased_n_candidates": len(biased),
        "unbiased_n_candidates": len(unbiased),
        "shared": len(both),
        "only_biased": len(only_biased),
        "only_unbiased": len(only_unbiased),
        "ranking_changes": [
            {
                "candidate": c,
                "biased_rank": biased[c]["rank"],
                "unbiased_rank": unbiased[c]["rank"],
                "delta": biased[c]["rank"] - unbiased[c]["rank"],
            }
            for c in common_sorted
        ],
        "new_in_unbiased": [
            {"candidate": c, **unbiased[c]} for c in only_u_sorted
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(compare_data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 对比结果保存到 {out_path}")


if __name__ == "__main__":
    main()
