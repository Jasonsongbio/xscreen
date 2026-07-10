"""文章候选 vs xscreen 交叉验证 + R/P/F1 评估

用文章的 22 个 qRT-PCR 引物候选作为 gold standard，评估 xscreen unbiased
corpus 的候选排名质量。生成：
  1. 完整交叉表（CSV + 终端打印）
  2. Recall/Precision/F1 @ K 曲线
  3. Figure 4（R/P/F1 矢量 PDF）

Gold 分级：
  Tier 1 (must-find): 文章 neuropeptidomic 阶段相反 + 选中 = NPF1a/AT/DH/sNPF
  Tier 2 (should-find): 文章做引物但非核心 = 其余 18 个
  Tier 3 (排除): 文章开头排除 = octopamine/dopamine

用法：
    python tools/paper_validation.py
"""
import sys
import json
import csv
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# 文章 22 个神经肽引物候选 + 角色 + qPCR 结果
# 来源：manuscript_r1.md P53-P55, P65-67 + supple-2.docx Table 1
PAPER_CANDIDATES = {
    # candidate_name: {role, qpcr_result, tier, match_patterns}
    "NPF1a": {
        "role": "主角（neuropeptidomic 选中）",
        "qpcr": "pre-Vite 脑 -48.1%; Vite 脑 +78.6%（大变化，脑内）",
        "tier": 1,
        "patterns": ["NPF"],  # 排除 sNPF/NPFR 的精确匹配在代码里处理
    },
    "AT": {
        "role": "neuropeptidomic 候选，qPCR 后淘汰",
        "qpcr": "Vite AG -16.6%（小变化，外周）",
        "tier": 1,
        "patterns": ["allatotropin", "Manse-AT", "Mas-AT", "Mas-allatotropin"],
    },
    "DH": {
        "role": "neuropeptidomic 候选，qPCR 后淘汰",
        "qpcr": "pre-Vite AG -26%（小变化，外周）",
        "tier": 1,
        "patterns": ["DH31", "DH44", "diuretic hormone"],
    },
    "sNPF": {
        "role": "neuropeptidomic 候选，qPCR 后淘汰",
        "qpcr": "Vite OL -21.8%（小变化，外周）",
        "tier": 1,
        "patterns": ["sNPF", "short NPF", "short neuropeptide F"],
    },
    "AKH I": {
        "role": "Discussion（代谢互补）",
        "qpcr": "AKH II pre-Vite 降; AKH I Vite 升",
        "tier": 2,
        "patterns": ["AKH", "adipokinetic"],
    },
    "AKH II": {
        "role": "Discussion（代谢互补）",
        "qpcr": "见 AKH I",
        "tier": 2,
        "patterns": ["AKH", "adipokinetic"],
    },
    "ALP": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["ALP", "adipokinetic-like"],
    },
    "AST-A": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["AstA", "allatostatin A", "allatostatin-A", "AST-A"],
    },
    "AST-B": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["AstB", "allatostatin B", "MIP", "myoinhibitory", "AST-B"],
    },
    "AST-C": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["AstC", "allatostatin C", "AST-C"],
    },
    "CCAP": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["CCAP", "crustacean cardioactive"],
    },
    "Dms": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["Dms", "DMS"],
    },
    "FMRFa": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["FMRFamide", "FMRFa", "FaRP", "FLRFamide"],
    },
    "ILP1": {
        "role": "引言提及（ILPs antagonize SIH）",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["ILP", "insulin-like", "DILP"],
    },
    "IRP": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["IRP", "insulin-related"],
    },
    "ITP": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["ITP", "ion transport"],
    },
    "Kin": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["leucokinin", "locustakinin", "kinin"],
    },
    "NPLP": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["NPLP", "neuropeptide-like precursor"],
    },
    "NTL": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["neurotensin", "NTL"],
    },
    "Orc": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["orcokinin"],
    },
    "PDF": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["PDF", "pigment-dispersing"],
    },
    "TK": {
        "role": "引物测了，未在正文展开",
        "qpcr": "—",
        "tier": 2,
        "patterns": ["tachykinin", "LomTK", "locustatachykinin"],
    },
}

# 文章明确排除的（受体/酶无变化）
PAPER_EXCLUDED = {
    "octopamine": {"role": "文章排除（受体/酶无变化）", "tier": "excluded"},
    "dopamine": {"role": "文章排除（受体/酶无变化）", "tier": "excluded"},
}


def load_xscreen_ranking(db_path: str) -> tuple[dict, list]:
    """加载 xscreen ranked list，返回 (stats_by_cand, ranked_list)。"""
    db = json.load(open(db_path, encoding="utf-8"))
    ev_by_cand = defaultdict(list)
    for ev in db["evidence"]:
        ev_by_cand[ev["core_name"]].append(ev)

    cand_stats = {}
    for c, evs in ev_by_cand.items():
        studies = len(set(e["source_pmid"] for e in evs))
        levels = defaultdict(int)
        for e in evs:
            levels[e["evidence_level"]] += 1
        cand_stats[c] = {
            "studies": studies,
            "evidence": len(evs),
            "levels": dict(levels),
        }

    # 按 studies 降序排（与 score.py 用 min_studies 一致，studies 是主驱动）
    ranked = sorted(cand_stats.items(), key=lambda x: (-x[1]["studies"], -x[1]["evidence"]))
    rank_map = {c: i + 1 for i, (c, _) in enumerate(ranked)}
    for c in cand_stats:
        cand_stats[c]["rank"] = rank_map[c]
    return cand_stats, [c for c, _ in ranked]


def match_candidate(patterns: list, cand_stats: dict, exclude_substrings: list = None) -> tuple:
    """在 xscreen 候选里匹配，返回 (best_match, rank, stats) 或 (None, None, None)。"""
    exclude_substrings = exclude_substrings or []
    matches = []
    for db_cand in cand_stats:
        dc = db_cand.lower()
        # 排除子串（如 NPF 匹配时排除 sNPF/NPFR）
        if any(ex.lower() in dc for ex in exclude_substrings):
            continue
        for pat in patterns:
            if pat.lower() == dc:
                matches.append((db_cand, "exact"))
                break
        else:
            for pat in patterns:
                if pat.lower() in dc:
                    matches.append((db_cand, "substr"))
                    break
    if not matches:
        return (None, None, None)
    # 优先 exact，再按 studies
    matches.sort(key=lambda m: (m[1] != "exact", -cand_stats[m[0]]["studies"]))
    best = matches[0][0]
    return (best, cand_stats[best]["rank"], cand_stats[best])


def build_cross_table(cand_stats: dict) -> list:
    """构建交叉表，返回 list of dict。"""
    rows = []
    for paper_name, info in PAPER_CANDIDATES.items():
        exclude = []
        if paper_name == "NPF1a":
            exclude = ["sNPF", "NPFR", "receptor"]  # NPF 本体排除 sNPF/受体
        if paper_name == "sNPF":
            exclude = ["receptor"]  # sNPF 排除受体
        best, rank, stats = match_candidate(info["patterns"], cand_stats, exclude)
        levels_str = ""
        if stats:
            lv = stats["levels"]
            order = ["functional", "peptide", "release", "transcript", "review_mention"]
            levels_str = " ".join(f"{k[:2].upper()}:{lv[k]}" for k in order if k in lv)
        rows.append({
            "paper_candidate": paper_name,
            "tier": info["tier"],
            "role": info["role"],
            "qpcr_result": info["qpcr"],
            "xscreen_match": best or "(未匹配)",
            "xscreen_rank": rank if rank else "—",
            "studies": stats["studies"] if stats else 0,
            "evidence": stats["evidence"] if stats else 0,
            "levels": levels_str,
            "hit_top30": "✓" if rank and rank <= 30 else ("△" if rank else "✗"),
            "hit_top50": "✓" if rank and rank <= 50 else ("△" if rank else "✗"),
        })
    return rows


def compute_rpf(cand_stats: dict, ranked_list: list, rows: list, max_k: int = 100) -> dict:
    """计算 Recall/Precision/F1 @ K。

    Gold = 文章 tier 1+2 候选（去重后的匹配名集合）。
    """
    # Gold: 从 rows 提取成功匹配的 xscreen 候选名（去重）
    gold = set()
    tier1_gold = set()
    for r in rows:
        if r["xscreen_match"] != "(未匹配)":
            gold.add(r["xscreen_match"])
            if r["tier"] == 1:
                tier1_gold.add(r["xscreen_match"])

    # @ K 计算
    results = {"gold_total": len(gold), "tier1_total": len(tier1_gold), "curves": []}
    for k in range(1, max_k + 1):
        topk = set(ranked_list[:k])
        hits = gold & topk
        hits_t1 = tier1_gold & topk
        recall = len(hits) / len(gold) if gold else 0
        precision = len(hits) / k if k else 0
        f1 = 2 * recall * precision / (recall + precision) if (recall + precision) else 0
        recall_t1 = len(hits_t1) / len(tier1_gold) if tier1_gold else 0
        results["curves"].append({
            "k": k,
            "recall": recall,
            "precision": precision,
            "f1": f1,
            "recall_tier1": recall_t1,
            "hits": len(hits),
            "hits_tier1": len(hits_t1),
        })
    return results


def main():
    db_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"
    if not db_path.exists():
        print(f"ERROR: {db_path} 不存在")
        sys.exit(1)

    cand_stats, ranked_list = load_xscreen_ranking(str(db_path))
    rows = build_cross_table(cand_stats)

    # === 打印交叉表 ===
    print("=" * 110)
    print("文章 22 候选 × xscreen 完整交叉表")
    print("=" * 110)
    print(f"{'文章候选':<8} {'Tier':<5} {'角色':<28} {'xscreen匹配':<16} {'排名':<6} {'Studies':<8} {'Evidence':<8} {'top30'} {'等级分布'}")
    print("-" * 110)
    # 按 tier 再按排名排
    rows_sorted = sorted(rows, key=lambda r: (r["tier"], r["xscreen_rank"] if isinstance(r["xscreen_rank"], int) else 999))
    for r in rows_sorted:
        print(f"{r['paper_candidate']:<8} T{r['tier']:<4} {r['role']:<28} {r['xscreen_match']:<16} "
              f"#{r['xscreen_rank']!s:<5} {r['studies']:<8} {r['evidence']:<8} {r['hit_top30']:<4} {r['levels']}")

    # qPCR 详细（tier 1）
    print(f"\n=== Tier 1 候选 qPCR 结果 vs xscreen ===")
    for r in rows:
        if r["tier"] == 1:
            print(f"  {r['paper_candidate']}: {r['qpcr_result']}")
            print(f"    xscreen: #{r['xscreen_rank']} ({r['studies']} studies)")

    # === R/P/F1 ===
    rpf = compute_rpf(cand_stats, ranked_list, rows)
    print(f"\n=== Recall / Precision / F1 ===")
    print(f"Gold 总数（去重匹配）: {rpf['gold_total']}")
    print(f"Tier 1 总数: {rpf['tier1_total']}")
    print(f"\n{'K':<6} {'Recall':<10} {'Precision':<10} {'F1':<10} {'R(T1)':<10} {'hits':<6} {'hits_t1'}")
    print("-" * 60)
    for k in [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]:
        if k <= len(rpf["curves"]):
            c = rpf["curves"][k - 1]
            print(f"{k:<6} {c['recall']:<10.3f} {c['precision']:<10.3f} {c['f1']:<10.3f} "
                  f"{c['recall_tier1']:<10.3f} {c['hits']:<6} {c['hits_tier1']}")

    # 关键指标
    c30 = rpf["curves"][29]
    c50 = rpf["curves"][49] if len(rpf["curves"]) > 49 else rpf["curves"][-1]
    print(f"\n关键指标：")
    print(f"  Recall@30 = {c30['recall']:.3f}（tier1: {c30['recall_tier1']:.3f}）")
    print(f"  Precision@30 = {c30['precision']:.3f}")
    print(f"  F1@30 = {c30['f1']:.3f}")
    print(f"  Recall@50 = {c50['recall']:.3f}")

    # === 保存 CSV ===
    out_dir = PROJECT_ROOT / "cases/locust_sih/output_unbiased"
    csv_path = out_dir / "paper_validation_crosstab.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "paper_candidate", "tier", "role", "qpcr_result",
            "xscreen_match", "xscreen_rank", "studies", "evidence",
            "levels", "hit_top30", "hit_top50",
        ])
        writer.writeheader()
        for r in rows_sorted:
            writer.writerow(r)
    print(f"\n✓ 交叉表 CSV → {csv_path}")

    # R/P/F1 数据
    rpf_path = out_dir / "rpf_curves.json"
    with open(rpf_path, "w", encoding="utf-8") as f:
        json.dump(rpf, f, ensure_ascii=False, indent=2)
    print(f"✓ R/P/F1 曲线数据 → {rpf_path}")


if __name__ == "__main__":
    main()
