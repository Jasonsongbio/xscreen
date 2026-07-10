"""关键词匹配 baseline vs xscreen LLM 抽取

用主表 67 肽名 + aliases 在 1349 篇摘要上做关键词匹配（regex word boundary），
按出现篇数排名 = baseline 排名。对比 xscreen LLM 排名。

目的：证明 LLM 抽取有增量价值（不只是关键词匹配能做到的）。

对比指标：
1. top-K overlap（两方法的共有候选）
2. xscreen 独有候选（关键词 baseline 抓不到的 = LLM 增量）
3. Spearman 排名相关性（共有候选）
4. baseline 只能匹配主表内的 67 肽；xscreen 能发现主表外的新候选

用法：
    python tools/keyword_baseline.py
"""
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.coverage_check import load_master_list, normalize_name


def build_keyword_patterns(master: dict) -> dict[str, list[str]]:
    """每个主表肽 → regex pattern 列表（所有 aliases，word boundary）。"""
    patterns: dict[str, list[str]] = {}
    for name, info in master.items():
        names = [name] + info.get("aliases", [])
        # 过滤太短的（<3 字符）和纯数字
        valid = [n for n in names if len(n) >= 3 and not n.isdigit()]
        seen = set()
        pats = []
        for nm in valid:
            # escape regex 特殊字符
            esc = re.escape(nm)
            # 词边界（允许后跟数字/字母，如 NPF1a）
            pat = r"\b" + esc + r"\b"
            if pat not in seen:
                seen.add(pat)
                pats.append(pat)
        if pats:
            patterns[name] = pats
    return patterns


def count_keyword_hits(papers: list[dict], patterns: dict[str, list[str]]) -> dict[str, int]:
    """对每篇 abstract 搜索关键词，返回 {master_name: 命中篇数}。"""
    counts: dict[str, int] = defaultdict(int)
    for p in papers:
        abstract = (p.get("abstract") or "").lower()
        title = (p.get("title") or "").lower()
        text = abstract + " " + title
        if not text.strip():
            continue
        for name, pats in patterns.items():
            for pat in pats:
                if re.search(pat, text, re.IGNORECASE):
                    counts[name] += 1
                    break  # 一篇只算一次（任一 alias 命中即可）
    return counts


def main() -> int:
    papers_path = PROJECT_ROOT / "cases/locust_sih/unbiased_papers.json"
    master_path = PROJECT_ROOT / "cases/locust_sih/neuropeptide_master_list.md"
    ev_db_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"

    papers_data = json.loads(papers_path.read_text(encoding="utf-8"))
    # papers_json 可能是 {papers: [...]} 或 [...]
    papers = papers_data.get("papers", papers_data) if isinstance(papers_data, dict) else papers_data
    print(f"论文数: {len(papers)}")

    master = load_master_list(str(master_path))
    target_master = {k: v for k, v in master.items()
                     if v["category"] not in ("off_topic", "exclude")}
    print(f"主表目标肽数: {len(target_master)}")

    # 构建关键词 pattern
    patterns = build_keyword_patterns(target_master)
    print(f"关键词 pattern 肽数: {len(patterns)}")

    # 关键词匹配
    print(f"\n=== 关键词匹配中 ===")
    kw_counts = count_keyword_hits(papers, patterns)
    kw_ranked = sorted(kw_counts.items(), key=lambda x: x[1], reverse=True)
    print(f"命中肽数: {len(kw_ranked)} / {len(target_master)}")

    # xscreen ranked（从 evidence_db 的 candidates）
    db = json.loads(ev_db_path.read_text(encoding="utf-8"))
    xs_candidates = db.get("candidates", [])
    xs_ranked = sorted(xs_candidates, key=lambda c: c.get("total_score", 0), reverse=True)
    print(f"xscreen ranked 候选数: {len(xs_ranked)}")

    # === 对比 ===
    print(f"\n{'='*70}")
    print(f"关键词 Baseline vs xscreen LLM 对比")
    print(f"{'='*70}")

    # normalize 名字用于匹配
    def find_xs_match(kw_name: str, xs_list: list) -> int | None:
        """主表名在 xscreen ranked 里的排名（1-based）。"""
        kn = normalize_name(kw_name)
        aliases = target_master[kw_name].get("aliases", [])
        kns = [normalize_name(a) for a in aliases] + [kn]
        for rank, xc in enumerate(xs_list, 1):
            xn = normalize_name(xc["candidate"])
            for k in kns:
                if k == xn:
                    return rank
                if len(k) >= 4 and (k in xn or xn in k):
                    return rank
        return None

    # baseline top-30
    print(f"\n--- Baseline Top-30（关键词频次）vs xscreen 排名 ---")
    print(f"{'#':<4} {'主表肽':<18} {'关键词篇数':<10} {'xscreen rank'}")
    print("-" * 45)
    baseline_top = kw_ranked[:30]
    for i, (name, cnt) in enumerate(baseline_top, 1):
        xs_rank = find_xs_match(name, xs_ranked)
        xs_str = f"#{xs_rank}" if xs_rank else "—"
        print(f"{i:<4} {name:<18} {cnt:<10} {xs_str}")

    # xscreen top-30 有多少在 baseline 主表里
    print(f"\n--- xscreen Top-30 vs Baseline ---")
    xs_top30 = xs_ranked[:30]
    in_baseline = 0
    not_in_baseline = []
    for xc in xs_top30:
        # 检查 xscreen 候选是否在 baseline 命中的主表肽里
        xn = normalize_name(xc["candidate"])
        found = False
        for name, cnt in kw_counts.items():
            kn = normalize_name(name)
            aliases = target_master[name].get("aliases", [])
            kns = [normalize_name(a) for a in aliases] + [kn]
            if any(xn == k or (len(k) >= 4 and (k in xn or xn in k)) for k in kns):
                found = True
                break
        if found:
            in_baseline += 1
        else:
            not_in_baseline.append(xc["candidate"])
    print(f"  在 baseline 主表内: {in_baseline}/30")
    print(f"  xscreen 独有（主表外或关键词漏）: {30 - in_baseline}/30")
    print(f"  独有候选: {not_in_baseline}")

    # LLM 增量：xscreen 浮上来但关键词 baseline 漏的候选
    # 这些是 LLM 的真正增量（能识别关键词匹配不到的候选）
    print(f"\n=== LLM 增量价值 ===")
    # xscreen 全部候选 vs baseline 全部命中
    xs_all_names = {normalize_name(c["candidate"]) for c in xs_ranked}
    baseline_all_names = set()
    for name in kw_counts:
        kn = normalize_name(name)
        baseline_all_names.add(kn)
        for a in target_master[name].get("aliases", []):
            baseline_all_names.add(normalize_name(a))

    # xscreen 候选不在 baseline 集合（LLM 发现的关键词抓不到的候选）
    xs_only = set()
    for c in xs_ranked:
        xn = normalize_name(c["candidate"])
        matched = False
        for bn in baseline_all_names:
            if xn == bn or (len(bn) >= 4 and (bn in xn or xn in bn)):
                matched = True
                break
        if not matched:
            xs_only.add(c["candidate"])

    print(f"xscreen 总候选: {len(xs_ranked)}")
    print(f"baseline 关键词命中主表肽: {len(kw_ranked)}")
    print(f"xscreen 独有（关键词 baseline 抓不到）: {len(xs_only)}")
    print(f"  → 这 {len(xs_only)} 个候选是 LLM 抽取的增量价值")

    # 保存
    out_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/keyword_baseline.json"
    out = {
        "description": "Keyword regex baseline vs xscreen LLM extraction",
        "n_papers": len(papers),
        "n_master_peptides": len(target_master),
        "baseline_hit_peptides": len(kw_ranked),
        "baseline_top30": [{"rank": i + 1, "peptide": n, "paper_count": c}
                           for i, (n, c) in enumerate(kw_ranked[:30])],
        "xscreen_only_count": len(xs_only),
        "xscreen_only_sample": sorted(xs_only)[:40],
        "overlap_in_top30": in_baseline,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ 结果保存到 {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
