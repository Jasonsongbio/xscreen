"""合并 gold 评估：原 29 review gold + 8 paper wet-lab = 37 gold vs xscreen unbiased 输出。

三层对比：
  1. 集合级 R/P/F1（复用 tools.eval_vs_gold.evaluate）—— 原 29 vs 合并 37
  2. @ K 曲线（Recall/Precision/F1 vs K，含 high-tier recall）—— 两 gold 并排
  3. 逐候选命中表（合并 37 候选，每个标 hit/miss + xscreen rank + source）

方法论：合并 gold 的 8 个新候选来自独立湿实验来源（论文引物表），不继承
biased corpus 的 NPF 文献圈偏差，也不继承 Drosophila-centric 偏差。

用法：
    python tools/eval_merged_gold.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.eval_vs_gold import evaluate, _normalize

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = PROJECT_ROOT / "cases/locust_sih"
OUT_DIR = CASE_DIR / "output_unbiased"

GOLD_ORIGINAL = CASE_DIR / "gold_standard.json"
GOLD_MERGED = CASE_DIR / "gold_standard_merged.json"
EV_DB = OUT_DIR / "evidence_db.json"


def load_ranked(ev_db_path: Path) -> list[str]:
    """从 evidence_db.json 的 candidates 字段取 ranked list（按 total_score 降序）。"""
    data = json.loads(Path(ev_db_path).read_text(encoding="utf-8"))
    cands = data.get("candidates", [])
    ranked = sorted(cands, key=lambda c: c.get("total_score", 0), reverse=True)
    return [c["candidate"] for c in ranked]


def find_xs_match(names: list[str], xs_norm_set: set[str]) -> str | None:
    """返回匹配的 xs normalized name，或 None。

    复用 eval_vs_gold._matches 的规则：精确，或单向前缀（len>=4）。
    """
    for nm in names:
        gn = _normalize(nm)
        if not gn:
            continue
        if gn in xs_norm_set:
            return gn
        if len(gn) >= 4:
            for xs in xs_norm_set:
                if xs.startswith(gn) or gn.startswith(xs):
                    return xs
    return None


def xs_in_gold(xn: str, gold_norm_set: set[str]) -> bool:
    """反向匹配：xscreen 候选是否落在 gold 集合里。"""
    if xn in gold_norm_set:
        return True
    if len(xn) >= 4:
        for gn in gold_norm_set:
            if gn.startswith(xn) or xn.startswith(gn):
                return True
    return False


def build_gold_norm_set(gold: dict) -> set[str]:
    """gold 所有名字（含 aliases）的 normalize 集合。"""
    s = set()
    for cand in gold["candidates"]:
        names = [cand["name"]] + cand.get("aliases", [])
        for nm in names:
            s.add(_normalize(nm))
    return s


def compute_rpf_at_k(gold: dict, xs_ranked: list[str], max_k: int = 100) -> list[dict]:
    """@ K 曲线：Recall / Precision / F1 / high-tier Recall。"""
    xs_norm_ranked = [_normalize(c) for c in xs_ranked]
    xs_norm_set = set(xs_norm_ranked)
    gold_norm_set = build_gold_norm_set(gold)

    # 预算每个 gold 候选匹配到的 xs norm（在整个 xs 池里，不限 top-k）
    gold_match: dict[str, str | None] = {}
    for cand in gold["candidates"]:
        names = [cand["name"]] + cand.get("aliases", [])
        gold_match[cand["name"]] = find_xs_match(names, xs_norm_set)

    n_gold = len(gold["candidates"])
    n_high = sum(1 for c in gold["candidates"] if c["relevance"] == "high")

    curves = []
    upper = min(max_k, len(xs_norm_ranked))
    for k in range(1, upper + 1):
        topk_norm = set(xs_norm_ranked[:k])
        hits = sum(1 for mn in gold_match.values() if mn and mn in topk_norm)
        hits_high = sum(
            1 for c in gold["candidates"]
            if c["relevance"] == "high"
            and gold_match[c["name"]] and gold_match[c["name"]] in topk_norm
        )
        in_gold_k = sum(1 for xn in xs_norm_ranked[:k] if xs_in_gold(xn, gold_norm_set))
        recall = hits / n_gold if n_gold else 0.0
        precision = in_gold_k / k if k else 0.0
        f1 = 2 * recall * precision / (recall + precision) if (recall + precision) else 0.0
        recall_high = hits_high / n_high if n_high else 0.0
        curves.append({
            "k": k, "recall": recall, "precision": precision, "f1": f1,
            "recall_high": recall_high, "hits": hits, "hits_high": hits_high,
        })
    return curves


def per_candidate_table(gold: dict, xs_ranked: list[str]) -> list[dict]:
    """逐候选命中表。"""
    xs_norm_set = set(_normalize(c) for c in xs_ranked)
    rank_map = {_normalize(c): i + 1 for i, c in enumerate(xs_ranked)}
    rows = []
    for cand in gold["candidates"]:
        names = [cand["name"]] + cand.get("aliases", [])
        mn = find_xs_match(names, xs_norm_set)
        rank = rank_map.get(mn) if mn else None
        rows.append({
            "name": cand["name"],
            "relevance": cand["relevance"],
            "source": cand.get("source", "review"),
            "hit": bool(mn),
            "xscreen_rank": rank,
            "in_reviews": cand.get("in_reviews", []),
        })
    return rows


def main() -> int:
    if not GOLD_MERGED.exists():
        print(f"ERROR: {GOLD_MERGED} 不存在")
        return 2
    if not EV_DB.exists():
        print(f"ERROR: {EV_DB} 不存在")
        return 2

    xs_ranked = load_ranked(EV_DB)
    print(f"xscreen ranked candidates: {len(xs_ranked)}")

    gold_orig = json.loads(GOLD_ORIGINAL.read_text(encoding="utf-8"))
    gold_merg = json.loads(GOLD_MERGED.read_text(encoding="utf-8"))

    # === 1. 集合级对比 ===
    print("\n" + "=" * 72)
    print("集合级评估对比（Set-level R/P/F1）")
    print("=" * 72)

    set_results = {}
    for label, gold_path, gold_obj in [
        ("原 29 gold (review-only)", GOLD_ORIGINAL, gold_orig),
        ("合并 37 gold (+8 paper)", GOLD_MERGED, gold_merg),
    ]:
        result = evaluate(gold_path, EV_DB)
        set_results[label] = result
        print(f"\n--- {label} ---")
        print(f"  Gold={result['n_gold']}  xscreen={result['n_xscreen']}  "
              f"hits={result['n_hit']}  extras={result['n_extras']}")
        print(f"  Recall={result['recall']:.3f}  Precision={result['precision']:.3f}  "
              f"F1={result['f1']:.3f}")
        for tier in ("high", "medium", "low"):
            t = result["tiers"][tier]
            r = t["hit"] / t["total"] if t["total"] else 0.0
            miss = ", ".join(t["miss"]) if t["miss"] else "—"
            print(f"    {tier:<8} {t['hit']}/{t['total']} = {r:.3f}  miss: {miss}")

    # === 2. @ K 曲线对比 ===
    print("\n" + "=" * 72)
    print("@ K 曲线对比（Recall / Precision / F1）")
    print("=" * 72)

    curves_orig = compute_rpf_at_k(gold_orig, xs_ranked, max_k=100)
    curves_merg = compute_rpf_at_k(gold_merg, xs_ranked, max_k=100)

    print(f"\n{'K':<5} {'R_29':<7} {'P_29':<7} {'F1_29':<7} {'R_h29':<7} | "
          f"{'R_37':<7} {'P_37':<7} {'F1_37':<7} {'R_h37':<7}  ΔR   ΔF1")
    print("-" * 88)
    for k in [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]:
        co = curves_orig[k - 1] if k <= len(curves_orig) else curves_orig[-1]
        cm = curves_merg[k - 1] if k <= len(curves_merg) else curves_merg[-1]
        dr = cm["recall"] - co["recall"]
        df1 = cm["f1"] - co["f1"]
        print(f"{k:<5} {co['recall']:<7.3f} {co['precision']:<7.3f} {co['f1']:<7.3f} "
              f"{co['recall_high']:<7.3f} | "
              f"{cm['recall']:<7.3f} {cm['precision']:<7.3f} {cm['f1']:<7.3f} "
              f"{cm['recall_high']:<7.3f}  {dr:+.3f} {df1:+.3f}")

    # === 3. 逐候选命中表（合并 gold） ===
    print("\n" + "=" * 72)
    print("合并 gold 37 候选逐个命中表（按 tier + rank）")
    print("=" * 72)

    rows = per_candidate_table(gold_merg, xs_ranked)
    # 排序：tier high 优先，然后按 rank（hit 的在前，miss 在后）
    rows.sort(key=lambda r: (r["relevance"] != "high",
                             0 if r["hit"] else 1,
                             r["xscreen_rank"] if r["xscreen_rank"] else 9999))

    print(f"\n{'Gold候选':<16} {'Tier':<8} {'Source':<24} {'Hit':<5} {'xscreen rank'}")
    print("-" * 70)
    for r in rows:
        rank_str = f"#{r['xscreen_rank']}" if r["xscreen_rank"] else "—"
        print(f"{r['name']:<16} {r['relevance']:<8} {r['source']:<24} "
              f"{'✓' if r['hit'] else '✗':<5} {rank_str}")

    # 保存数据
    out_path = OUT_DIR / "rpf_curves_merged.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "description": "R/P/F1 @ K for merged gold (37) vs original gold (29)",
            "gold_original_size": len(gold_orig["candidates"]),
            "gold_merged_size": len(gold_merg["candidates"]),
            "set_level": {
                "original_29": {k: v for k, v in set_results["原 29 gold (review-only)"].items()
                                if k in ("n_gold", "n_xscreen", "n_hit", "n_extras",
                                         "recall", "precision", "f1")},
                "merged_37": {k: v for k, v in set_results["合并 37 gold (+8 paper)"].items()
                              if k in ("n_gold", "n_xscreen", "n_hit", "n_extras",
                                       "recall", "precision", "f1")},
            },
            "curves_original": curves_orig,
            "curves_merged": curves_merg,
            "per_candidate": rows,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 数据保存到 {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
