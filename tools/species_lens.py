"""Species lens：target-species 聚焦排名。

从 evidence_db 筛 target_species（如 Locusta migratoria）相关 evidence，
单独排名。用途：锁定 locust-native 候选（如 NPF1a），辅助湿实验锚定。

主排名基于全量 corpus（Drosophila 文献为主），locust 特异基因（NPF1a）
证据天然稀少，进不了 top-30。Lens 视图只看 target-species 证据，让这些
候选凸显——不改主排名，只提供补充视角。

用法：
    python tools/species_lens.py cases/locust_sih/config_unbiased.yaml
"""
import sys
import copy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402
from src import score  # noqa: E402
from tools.score_unbiased import load_evidence  # noqa: E402

# Locusta 近缘属（target=Locusta migratoria 时扩展匹配，覆盖 locust 近缘种）
_LOCUST_GENERA = ("locusta", "schistocerca", "gastrimargus", "valanga",
                  "romalea", "melanoplus")


def _is_target_species(species: str, target: str) -> bool:
    """判断 evidence 的 species 是否属于 target species（属名匹配）。

    Locusta migratoria 作为 target 时，扩展到 locust 近缘属（Schistocerca
    等），因为 locust 神经肽文献常跨属报告。
    """
    s = (species or "").lower()
    t = (target or "").lower()
    if not s or not t:
        return False
    # 精确属名匹配
    if t.split()[0] in s:
        return True
    # locust 特殊：扩展到近缘属 + 泛称 "locust"
    if "locust" in t or "migratoria" in t:
        return any(g in s for g in _LOCUST_GENERA) or "locust" in s
    return False


def build_lens(evidence_list, target):
    """筛 target-species evidence 子集。"""
    return [ev for ev in evidence_list if _is_target_species(ev.species, target)]


def run_lens(config, lens_evidence, top_n=30):
    """对 lens evidence 子集排名（复用 score，min_studies=1 适配稀疏证据）。"""
    lens_config = copy.deepcopy(config)
    lens_config.setdefault("scoring", {})["min_studies"] = 1
    lens_config["scoring"]["top_n"] = top_n
    candidates = sorted({ev.core_name for ev in lens_evidence})
    ortholog_map = {c: None for c in candidates}
    return score.run(lens_config, lens_evidence, ortholog_map)


def main():
    if len(sys.argv) != 2:
        print("Usage: python tools/species_lens.py <config.yaml>")
        sys.exit(1)

    config = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
    target = config["study"]["target_species"]
    case_dir = Path(sys.argv[1]).parent
    out_dir = case_dir / config["output"]["dir"]
    db_path = out_dir / config["output"]["database"]

    if not db_path.exists():
        print(f"ERROR: {db_path} 不存在，先跑 extract + score")
        sys.exit(1)

    evidence_list = load_evidence(str(db_path))
    lens_evidence = build_lens(evidence_list, target)

    print(f"=== Species Lens: {target} ===")
    print(f"总 evidence: {len(evidence_list)}")
    print(f"{target} 相关 evidence: {len(lens_evidence)}")

    if not lens_evidence:
        print("无 target species 证据，退出")
        return

    scores = run_lens(config, lens_evidence)
    print(f"\n=== {target} Lens Top {min(20, len(scores))} ===")
    print(f"{'Rank':<5} {'Candidate':<28} {'Score':<8} {'Studies':<8} {'Evidence':<8}")
    print("-" * 70)
    for i, s in enumerate(scores[:20], 1):
        print(f"{i:<5} {s.candidate:<28} {s.total_score:<8.3f} "
              f"{s.study_count:<8} {s.evidence_count:<8}")

    # NPF1a / NPF 在 lens 的排名（反 confirmation bias 检验）
    npf1a = [i + 1 for i, s in enumerate(scores) if "NPF1A" in s.candidate.upper()]
    npf = [i + 1 for i, s in enumerate(scores)
           if s.candidate.upper() == "NPF" or s.candidate.upper() == "NPF "]
    print(f"\n=== locust-native 候选 lens 排名 ===")
    print(f"NPF1a: rank {npf1a if npf1a else '未进榜'}")
    print(f"NPF:   rank {npf if npf else '未进榜'}")

    # 保存 markdown
    lens_path = out_dir / "species_lens_locusta.md"
    lines = [
        f"# Species Lens: {target}\n",
        f"target-species evidence: {len(lens_evidence)}/{len(evidence_list)} "
        f"({len(lens_evidence)/len(evidence_list)*100:.1f}%)\n",
        "\n## Lens Ranking (target-species evidence only)\n",
        "| Rank | Candidate | Score | Studies | Evidence |",
        "|---|---|---|---|---|",
    ]
    for i, s in enumerate(scores[:30], 1):
        lines.append(f"| {i} | {s.candidate} | {s.total_score:.3f} | "
                     f"{s.study_count} | {s.evidence_count} |")
    lens_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✓ 保存到 {lens_path}")


if __name__ == "__main__":
    main()
