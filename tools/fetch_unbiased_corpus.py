"""无偏 corpus 检索脚本（策略 A）

用途：跑 Level 2 同义扩展 query（不含候选名），收集 PubMed 论文元数据 + 摘要。
输出：cases/locust_sih/unbiased_papers.json

遵循 7 步预判流程的 Step 6（检索量预估）+ Step 7（抽样验证）。

关键防偏置原则：
1. 不写候选名（NPF/AKH/DH44/allatotropin/NPY 等）—— 答案必须由工具独立浮上来
2. 不写 SIH（用同义扩展代替）—— SIH 是 locust 黑话，仅 33 hits
3. 物种同等并列 —— 不在 query 里优先 Drosophila
4. [TIAB] 限制 —— 避免 MeSH 索引偏置
"""
import os
import json
import time
import argparse
from pathlib import Path
from io import StringIO

from Bio import Entrez, Medline


def load_env(path: str = ".env") -> None:
    """手动加载 .env（避开 dotenv frame 问题）"""
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v


# Level 2 无偏 query（来自 query_preassessment.md）
UNBIASED_QUERY = """(
  insect[TIAB] OR insects[TIAB] OR Drosophila[TIAB]
  OR Locusta[TIAB] OR Schistocerca[TIAB]
  OR "Apis"[TIAB] OR "Bombyx"[TIAB] OR "Anopheles"[TIAB]
  OR "Tribolium"[TIAB] OR Manduca[TIAB]
)
AND
(
  starv*[TIAB] OR fast*[TIAB] OR "food deprivation"[TIAB]
  OR hunger[TIAB] OR hung*[TIAB]
  OR feed*[TIAB] OR ingest*[TIAB] OR forag*[TIAB]
  OR locomot*[TIAB] OR hyperact*[TIAB] OR walking[TIAB]
  OR "energy homeostasis"[TIAB] OR metabolism[TIAB]
)
AND
(
  neuropeptide*[TIAB] OR "peptide hormone*"[TIAB]
  OR "biogenic amine*"[TIAB] OR neurotransmitter*[TIAB]
)
AND ("2000"[PDAT] : "2026"[PDAT])"""


def esearch_all_ids(query: str, batch_size: int = 10000) -> list[str]:
    """esearch 拉取所有 PMID（单次 retmax 已足够，1349 篇）"""
    h = Entrez.esearch(db="pubmed", term=query, retmax=batch_size)
    r = Entrez.read(h)
    h.close()
    ids = r["IdList"]
    print(f"  esearch 命中 {r['Count']} 篇，取回 {len(ids)} 个 PMID")
    return ids


def efetch_batch(ids: list[str], batch_size: int = 200) -> list[dict]:
    """分批 efetch（每批 200 篇），返回 Medline 解析的 record dict 列表"""
    all_records: list[dict] = []
    total_batches = (len(ids) + batch_size - 1) // batch_size
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        t0 = time.time()
        for attempt in range(3):
            try:
                h = Entrez.efetch(
                    db="pubmed",
                    id=",".join(batch),
                    rettype="medline",
                    retmode="text",
                )
                raw = h.read()
                h.close()
                records = list(Medline.parse(StringIO(raw)))
                all_records.extend(records)
                print(f"  batch {batch_num}/{total_batches}: {len(batch)} PMID -> {len(records)} records ({time.time()-t0:.1f}s)")
                break
            except Exception as e:
                wait = 2 ** attempt
                print(f"  batch {batch_num} 失败 ({e}), {wait}s 后重试")
                time.sleep(wait)
        time.sleep(0.3)  # 礼貌延迟（API key 允许 10 req/s）
    return all_records


def record_to_dict(rec: dict, idx: int) -> dict:
    """Medline flat record -> 可序列化 dict"""
    pub_date = rec.get("DP", "1900")
    year_str = str(pub_date)[:4]
    year = int(year_str) if year_str.isdigit() else 1900
    doi = None
    for aid in rec.get("AID", []):
        if "[DOI]" in str(aid):
            doi = str(aid).replace(" [DOI]", "")
            break
    # 抽取 publication type 用于后续 review 判定
    pub_types = rec.get("PT", [])
    return {
        "id": f"PM{idx+1:04d}",
        "pmid": rec.get("PMID", ""),
        "doi": doi,
        "title": rec.get("TI", ""),
        "authors": rec.get("AU", []),
        "journal": rec.get("JT", ""),
        "year": year,
        "abstract": rec.get("AB", ""),
        "keywords": rec.get("OT", []),
        "publication_types": pub_types,
        "source": "pubmed",
    }


def main():
    parser = argparse.ArgumentParser(description="无偏 corpus 检索（策略 A）")
    parser.add_argument(
        "--output",
        default="cases/locust_sih/unbiased_papers.json",
        help="输出 JSON 路径",
    )
    parser.add_argument(
        "--query",
        default="level2",
        help="使用 level2 query（默认）或测试用小 query",
    )
    parser.add_argument("--dry-run", action="store_true", help="只 esearch，不 efetch")
    args = parser.parse_args()

    # 切到项目根目录加载 .env
    project_root = Path(__file__).resolve().parents[1]
    load_env(str(project_root / ".env"))

    Entrez.email = os.environ["NCBI_EMAIL"]
    Entrez.api_key = os.environ["NCBI_API_KEY"]

    print(f"=== 无偏 corpus 检索（策略 A, Level 2 query）===")
    print(f"NCBI email: {Entrez.email}")

    # Step 1: esearch 所有 PMID
    t0 = time.time()
    ids = esearch_all_ids(UNBIASED_QUERY)
    print(f"esearch 总耗时: {time.time()-t0:.1f}s\n")

    if args.dry_run:
        print("--dry-run 模式：跳过 efetch")
        return

    # Step 2: efetch 分批拉取
    print(f"=== 分批 efetch（每批 200 篇）===")
    t0 = time.time()
    records = efetch_batch(ids, batch_size=200)
    print(f"efetch 总耗时: {time.time()-t0:.1f}s\n")

    # Step 3: 转 dict + 去重（PMID 空/重复）
    seen_pmids: set[str] = set()
    papers: list[dict] = []
    for i, rec in enumerate(records):
        pmid = rec.get("PMID", "")
        if pmid and pmid in seen_pmids:
            continue
        if pmid:
            seen_pmids.add(pmid)
        papers.append(record_to_dict(rec, len(papers)))

    # Step 4: 统计
    n_with_abstract = sum(1 for p in papers if p["abstract"])
    n_review = sum(1 for p in papers if any("Review" in pt for pt in p["publication_types"]))
    years = [p["year"] for p in papers if p["year"] > 1900]

    print(f"=== 检索结果统计 ===")
    print(f"总论文数: {len(papers)}")
    print(f"有摘要: {n_with_abstract} ({100*n_with_abstract/len(papers):.1f}%)")
    print(f"PubMed 标记 Review: {n_review}")
    if years:
        print(f"年份范围: {min(years)}-{max(years)}")
    print(f"输出: {args.output}")

    # Step 5: 保存
    out_path = project_root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "query": UNBIASED_QUERY,
            "n_papers": len(papers),
            "n_with_abstract": n_with_abstract,
            "n_review": n_review,
            "papers": papers,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 已保存 {len(papers)} 篇到 {out_path}")


if __name__ == "__main__":
    main()
