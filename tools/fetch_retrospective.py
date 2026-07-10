"""回溯性 corpus 检索（2000-2015）

用同样 unbiased query，日期限 2000-2015，用于回溯性预测验证。
对比 2016-2026 corpus，看 2000-2015 的 top 候选是否在 2016-2026 被研究。

复用 fetch_unbiased_corpus 的函数（DRY），只改 query 日期 + 输出路径。

用法：
    python tools/fetch_retrospective.py
"""
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from fetch_unbiased_corpus import (
    load_env, UNBIASED_QUERY, esearch_all_ids, efetch_batch, record_to_dict
)

RETRO_QUERY = UNBIASED_QUERY.replace(
    '"2000"[PDAT] : "2026"[PDAT]',
    '"2000"[PDAT] : "2015"[PDAT]',
)


def main() -> int:
    import os
    from Bio import Entrez

    load_env(str(PROJECT_ROOT / ".env"))
    Entrez.email = os.environ["NCBI_EMAIL"]
    Entrez.api_key = os.environ["NCBI_API_KEY"]

    print(f"=== 回溯性 corpus 检索（2000-2015）===")

    t0 = time.time()
    ids = esearch_all_ids(RETRO_QUERY)
    print(f"esearch 耗时: {time.time()-t0:.1f}s\n")

    print(f"=== 分批 efetch ===")
    t0 = time.time()
    records = efetch_batch(ids, batch_size=200)
    print(f"efetch 耗时: {time.time()-t0:.1f}s\n")

    seen: set[str] = set()
    papers = []
    for rec in records:
        pmid = rec.get("PMID", "")
        if pmid and pmid in seen:
            continue
        if pmid:
            seen.add(pmid)
        papers.append(record_to_dict(rec, len(papers)))

    n_abs = sum(1 for p in papers if p["abstract"])
    n_rev = sum(1 for p in papers if any("Review" in pt for pt in p["publication_types"]))
    years = [p["year"] for p in papers if p["year"] > 1900]

    print(f"=== 结果 ===")
    print(f"总论文: {len(papers)}")
    print(f"有摘要: {n_abs} ({100*n_abs/len(papers):.1f}%)")
    print(f"Review: {n_rev}")
    if years:
        print(f"年份: {min(years)}-{max(years)}")

    out_path = PROJECT_ROOT / "cases/locust_sih/retrospective_papers_2000_2015.json"
    out_path.write_text(json.dumps({
        "query": RETRO_QUERY,
        "period": "2000-2015",
        "n_papers": len(papers),
        "n_with_abstract": n_abs,
        "n_review": n_rev,
        "papers": papers,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ 保存 {len(papers)} 篇到 {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
