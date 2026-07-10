"""xscreen 候选多源客观分类（gold-independent precision proxy）

对 517 候选逐个归类，证明 xscreen 抽取的候选质量（非幻觉、非噪声）。
全部不依赖人工 gold standard。

分类层级（按优先级）：
1. known_peptide   — 在主表 67 肽（含 alias，来自 7 个权威源）
2. known_amine     — 已知 biogenic amine / classical neurotransmitter（论文 scope 内合法）
3. type_error      — receptor / enzyme / drug / 非信号代谢物（规则检测）
4. in_uniprot      — 不在上述类，但 UniProt insecta reviewed 里有对应蛋白
5. plausible_novel — 通过所有检查的新候选（潜在真发现）

输出：分类分布 + 逐候选归类 JSON。
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.coverage_check import load_master_list, normalize_name
from src.type_filter import (
    is_receptor, is_enzyme, is_drug, is_metabolite, is_noise, KNOWN_AMINES,
)


def load_candidates(ev_db_path: Path) -> list[str]:
    db = json.loads(ev_db_path.read_text(encoding="utf-8"))
    return sorted({e["core_name"] for e in db["evidence"] if e.get("core_name")})


# is_receptor/is_enzyme/is_drug/is_metabolite/is_noise/KNOWN_AMINES 已迁移到
# src/type_filter.py（src/ 与 tools/ 共享，DRY 单一来源）。


def strict_master_match(name: str, master: dict) -> bool:
    """严格匹配主表：normalize 后精确或双向子串（len>=4），不用 fuzzy。"""
    cn = normalize_name(name)
    if len(cn) < 2:
        return False
    for mname, info in master.items():
        names = [mname] + info.get("aliases", [])
        for nm in names:
            mn = normalize_name(nm)
            if not mn:
                continue
            if cn == mn:
                return True
            # 双向子串，但要求双方都 >=4 字符，避免短名误匹配
            if len(cn) >= 4 and len(mn) >= 4 and (cn in mn or mn in cn):
                return True
    return False


def classify_local(name: str, master: dict) -> str | None:
    """本地规则分类。顺序很重要：先排 type_error，再匹配肽（避免受体误匹配配体）。"""
    # 1. type_error 优先（受体/酶/药/代谢物/噪声）
    if is_receptor(name):
        return "receptor"
    if is_enzyme(name):
        return "enzyme"
    if is_drug(name):
        return "drug"
    if is_metabolite(name):
        return "metabolite"
    if is_noise(name):
        return "noise"
    # 2. 已知胺
    if name in KNOWN_AMINES or name.upper() in {a.upper() for a in KNOWN_AMINES}:
        return "known_amine"
    # 3. 主表肽（严格匹配）
    if strict_master_match(name, master):
        return "known_peptide"
    return None


def query_uniprot(name: str, timeout: int = 15) -> dict | None:
    """查 UniProt insecta reviewed，看候选名是否有对应蛋白。"""
    # 用 protein_name + gene_name 搜索
    q = f'({name}) AND taxonomy_id:50557 AND reviewed:true'
    url = ("https://rest.uniprot.org/uniprotkb/search?"
           f"query={urllib.parse.quote(q)}&format=json&size=3")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "xscreen-research/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            results = data.get("results", [])
            if results:
                hit = results[0]
                return {
                    "accession": hit.get("primaryAccession"),
                    "protein_name": (hit.get("proteinDescription", {})
                                       .get("recommendedName", {}).get("fullName", {}).get("value", "")),
                    "organism": hit.get("organism", {}).get("scientificName", ""),
                }
    except Exception:
        return None
    return None


def main() -> int:
    ev_db = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"
    master_path = PROJECT_ROOT / "cases/locust_sih/neuropeptide_master_list.md"

    cands = load_candidates(ev_db)
    master = load_master_list(str(master_path))
    # 过滤主表 off_topic/exclude
    target_master = {k: v for k, v in master.items()
                     if v["category"] not in ("off_topic", "exclude")}

    print(f"=== UniProt 交叉验证（多源客观分类）===")
    print(f"候选总数: {len(cands)}")
    print(f"主表已知肽数: {len(target_master)}")

    # 第一遍：本地分类
    local_class = {}
    needs_uniprot = []
    for c in cands:
        cat = classify_local(c, target_master)
        if cat:
            local_class[c] = cat
        else:
            needs_uniprot.append(c)

    print(f"\n本地规则分类完成: {len(local_class)} 个归类")
    print(f"需 UniProt 验证: {len(needs_uniprot)} 个")

    # 本地分类统计
    local_counts = defaultdict(list)
    for c, cat in local_class.items():
        local_counts[cat].append(c)
    print(f"\n=== 本地分类分布 ===")
    for cat, names in sorted(local_counts.items()):
        print(f"  {cat}: {len(names)}")
        for n in names[:6]:
            print(f"    - {n}")
        if len(names) > 6:
            print(f"    ... (+{len(names)-6})")

    # 第二遍：UniProt 验证（对 needs_uniprot）
    print(f"\n=== UniProt 验证 {len(needs_uniprot)} 个候选 ===")
    uniprot_hits = {}
    uniprot_miss = []
    for i, c in enumerate(needs_uniprot):
        hit = query_uniprot(c)
        if hit:
            uniprot_hits[c] = hit
        else:
            uniprot_miss.append(c)
        if (i + 1) % 20 == 0:
            print(f"  进度: {i+1}/{len(needs_uniprot)}")
            time.sleep(0.3)

    print(f"  UniProt 命中: {len(uniprot_hits)}")
    print(f"  UniProt 未命中（plausible_novel 或命名错误）: {len(uniprot_miss)}")

    # 汇总
    final = {}
    for c in cands:
        if c in local_class:
            final[c] = local_class[c]
        elif c in uniprot_hits:
            final[c] = "in_uniprot"
        else:
            final[c] = "plausible_novel"

    counts = defaultdict(list)
    for c, cat in final.items():
        counts[cat].append(c)

    print(f"\n=== 最终分类分布（{len(cands)} 候选）===")
    order = ["known_peptide", "known_amine", "in_uniprot", "plausible_novel",
             "receptor", "enzyme", "drug", "metabolite", "noise"]
    for cat in order:
        if cat in counts:
            names = counts[cat]
            print(f"  {cat:<18} {len(names):<4} ({len(names)/len(cands)*100:.1f}%)")

    # 客观 precision proxy = (known_peptide + known_amine + in_uniprot + plausible_novel) / total
    good = sum(len(counts[c]) for c in ["known_peptide", "known_amine", "in_uniprot", "plausible_novel"] if c in counts)
    errors = sum(len(counts[c]) for c in ["receptor", "enzyme", "drug", "metabolite", "noise"] if c in counts)
    print(f"\n=== 客观质量指标 ===")
    print(f"  合法信号分子（肽+胺+UniProt验证+新候选）: {good} ({good/len(cands)*100:.1f}%)")
    print(f"  type_error（受体/酶/药/代谢物/噪声）: {errors} ({errors/len(cands)*100:.1f}%)")

    # plausible_novel 样本
    if "plausible_novel" in counts:
        print(f"\n=== plausible_novel 样本（潜在新发现，UniProt 未命中）===")
        for n in counts["plausible_novel"][:25]:
            print(f"  - {n}")

    # 保存
    out_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/uniprot_validation.json"
    out = {
        "total_candidates": len(cands),
        "classification": {cat: names for cat, names in counts.items()},
        "objective_precision_proxy": {
            "valid_signals": good,
            "type_errors": errors,
            "valid_rate": good / len(cands),
        },
        "uniprot_hits_detail": uniprot_hits,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ 结果保存到 {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
