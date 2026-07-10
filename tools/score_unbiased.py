"""无偏 corpus 评分 + 报告生成

从 output_unbiased/evidence_db.json 加载 evidence，跑 score + report，
跳过 homolog（之前 UniProt 0/33 失败，是基础设施问题；设全 None，
ortholog_mult=0.5 统一缩放，不改变相对排名）。

用法：
    python tools/score_unbiased.py cases/locust_sih/config_unbiased.yaml
"""
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402
from src.extract import Evidence  # noqa: E402
from src import score, report  # noqa: E402


def load_evidence(json_path: str) -> list[Evidence]:
    """从 evidence_db.json 加载 evidence 列表。"""
    data = json.load(open(json_path, encoding="utf-8"))
    evidence = []
    for d in data["evidence"]:
        # 过滤 asdict 里 Evidence 没有的字段（防御）
        evidence.append(Evidence(
            id=d["id"],
            paper_id=d["paper_id"],
            candidate=d["candidate"],
            core_name=d["core_name"],
            candidate_type=d["candidate_type"],
            species=d["species"],
            evidence_level=d["evidence_level"],
            direction=d["direction"],
            quote=d["quote"],
            confidence=d["confidence"],
            source_pmid=d["source_pmid"],
            source_title=d["source_title"],
            behavior_effect=d.get("behavior_effect"),
            expression_location=d.get("expression_location"),
        ))
    return evidence


def main():
    if len(sys.argv) != 2:
        print("Usage: python tools/score_unbiased.py <config.yaml>")
        sys.exit(1)

    config_path = sys.argv[1]
    config = yaml.safe_load(open(config_path, encoding="utf-8"))

    out_dir = PROJECT_ROOT / "cases/locust_sih" / config["output"]["dir"]
    db_path = out_dir / config["output"]["database"]

    if not db_path.exists():
        print(f"ERROR: {db_path} 不存在，先跑 extract_unbiased.py")
        sys.exit(1)

    print(f"=== 无偏 corpus 评分 ===")
    evidence_list = load_evidence(str(db_path))
    print(f"加载 {len(evidence_list)} 条 evidence")

    # 跳过 homolog：所有候选 ortholog=None
    candidates = sorted({ev.core_name for ev in evidence_list})
    ortholog_map = {c: None for c in candidates}
    print(f"候选数（去重 core_name）: {len(candidates)}")
    print(f"Homolog: 跳过（全部 None，ortholog_mult=0.5 统一缩放）")

    # 评分
    print(f"\n=== 评分（min_studies={config['scoring']['min_studies']}, top_n={config['scoring']['top_n']}）===")
    scores = score.run(config, evidence_list, ortholog_map)
    print(f"通过 min_studies 过滤的候选: {len(scores)}")

    if not scores:
        print("无候选通过过滤，检查 min_studies 设置")
        return

    # 打印 top 30
    print(f"\n=== Top {min(30, len(scores))} 候选 ===")
    print(f"{'Rank':<5} {'Candidate':<20} {'Score':<8} {'Studies':<8} {'Evidence':<8} {'Levels'}")
    print("-" * 80)
    from src.report import _format_evidence_levels
    for i, s in enumerate(scores[:30], 1):
        levels = _format_evidence_levels(s.evidence_levels)
        print(f"{i:<5} {s.candidate:<20} {s.total_score:<8.3f} {s.study_count:<8} {s.evidence_count:<8} {levels}")

    # 生成报告
    print(f"\n=== 生成报告 ===")
    report.run(config, out_dir, scores, evidence_list)
    print(f"✓ 输出到 {out_dir}/")
    print(f"  - {config['output']['table']}")
    print(f"  - {config['output']['database']}")
    print(f"  - {config['output']['report']}")

    # 关键问题：NPF 排第几？
    npf_ranks = [i+1 for i, s in enumerate(scores) if 'NPF' in s.candidate.upper()]
    akh_ranks = [i+1 for i, s in enumerate(scores) if 'AKH' in s.candidate.upper()]
    print(f"\n=== 关键候选排名（反 confirmation bias 检验）===")
    print(f"NPF: rank {npf_ranks if npf_ranks else '未进榜'}")
    print(f"AKH: rank {akh_ranks if akh_ranks else '未进榜'}")


if __name__ == "__main__":
    main()
