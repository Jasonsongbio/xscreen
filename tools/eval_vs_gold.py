"""Evaluate xscreen extraction against a gold-standard candidate list.

Compares the set of candidates extracted by xscreen (from evidence_db.json)
against a manually-curated gold standard (gold_standard.json), reporting
Recall, Precision, F1, and a gap analysis stratified by relevance tier.

双边规范化：xscreen 和 gold 的候选名在匹配前先过 src.normalize.normalize_core_name
（合并同义变体到主表 canonical 名），再做 _normalize 粗粒度匹配键。这样
"Allatotropin"（规范化后）能匹配 gold 里的 "AT"。

Usage:
    python -m tools.eval_vs_gold cases/locust_sih/config_real.yaml
    python tools/eval_vs_gold.py cases/locust_sih/config_real.yaml
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config_loader import get_output_dir, load_config
from src.normalize import build_alias_map, normalize_core_name
from tools.coverage_check import load_master_list

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _normalize(name: str) -> str:
    """Normalize a candidate name for matching: lowercase, strip suffixes/punctuation."""
    s = name.lower().strip()
    # collapse all non-alphanumeric
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _build_eval_alias_map(config: dict, case_dir: Path) -> dict[str, str] | None:
    """从 config.study.master_list 加载主表并构建 alias_map（用于双边规范化）。

    复用 src.normalize.build_alias_map + tools.coverage_check.load_master_list，
    与 src/score.py._load_alias_map 保持一致逻辑。

    Args:
        config: 已加载的 config dict。
        case_dir: case 目录（未使用，master_list 路径相对项目根）。

    Returns:
        alias_map dict，或 None（config 无 master_list 或加载失败时降级到纯 _normalize）。
    """
    master_path = config.get("study", {}).get("master_list")
    if not master_path:
        return None
    full_path = _PROJECT_ROOT / master_path
    if not full_path.exists():
        return None
    try:
        master = load_master_list(str(full_path))
    except Exception:
        return None
    target = {k: v for k, v in master.items()
              if v.get("category") not in ("off_topic", "exclude")}
    return build_alias_map(target)


def build_gold_alias_map(gold: dict) -> dict[str, dict]:
    """Return {normalized_name: gold_candidate_dict} incl. aliases."""
    mapping: dict[str, dict] = {}
    for cand in gold["candidates"]:
        names = [cand["name"]] + cand.get("aliases", [])
        for nm in names:
            mapping[_normalize(nm)] = cand
    return mapping


def _matches(names_list: list[str], xs_set: set[str], min_len: int = 4) -> bool:
    """Check if any name in names_list matches any xscreen entry.

    Match rules (after normalization): exact, or one is a prefix of the other
    (handles subtypes: gold 'allatostatin' <-> xscreen 'allatostatin A',
    gold 'CCHamide' <-> xscreen 'CCHamide-1'). Short names (<min_len) are
    exact-match only to avoid spurious prefix hits (e.g. 'MIP').
    """
    for nm in names_list:
        gn = _normalize(nm)
        if not gn:
            continue
        if gn in xs_set:
            return True
        if len(gn) >= min_len:
            for xs in xs_set:
                if xs.startswith(gn) or gn.startswith(xs):
                    return True
    return False


def _eval_normalize(name: str, alias_map: dict[str, str] | None) -> str:
    """双边规范化：先 normalize_core_name（合并同义变体），再 _normalize（生成比较键）。

    alias_map 为 None 时降级到纯 _normalize（兼容旧逻辑）。
    """
    if alias_map:
        name = normalize_core_name(name, alias_map)
    return _normalize(name)


def evaluate(gold_path: Path, evidence_db_path: Path,
             alias_map: dict[str, str] | None = None) -> dict:
    """Run the comparison. Returns a structured result dict.

    Args:
        gold_path: Path to gold_standard.json.
        evidence_db_path: Path to evidence_db.json (xscreen output).
        alias_map: Optional alias map from build_alias_map for bilateral
            core_name normalization. If None, falls back to pure _normalize.
    """
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    ev_db = json.loads(evidence_db_path.read_text(encoding="utf-8"))

    gold_alias = build_gold_alias_map(gold)
    # Bilateral normalize: normalize_core_name first, then _normalize for key.
    xs_set = {_eval_normalize(ev["core_name"], alias_map)
              for ev in ev_db.get("evidence", [])}

    # Per-tier analysis
    tiers = {"high": [], "medium": [], "low": []}
    gold_hit = []
    gold_miss = []
    for cand in gold["candidates"]:
        names = [cand["name"]] + cand.get("aliases", [])
        # Normalize gold names too before matching
        norm_names = [_eval_normalize(nm, alias_map) for nm in names]
        matched = _matches(norm_names, xs_set)
        entry = {"name": cand["name"], "relevance": cand["relevance"],
                 "matched": matched, "in_reviews": cand["in_reviews"]}
        tiers[cand["relevance"]].append(entry)
        (gold_hit if matched else gold_miss).append(entry)

    # xscreen extras (not in gold at all): an xs entry is "in gold" if it
    # matches any gold name under the same prefix rule.
    xs_in_gold: set[str] = set()
    for cand in gold["candidates"]:
        names = [cand["name"]] + cand.get("aliases", [])
        norm_names = [_eval_normalize(nm, alias_map) for nm in names]
        for gn in norm_names:
            if not gn:
                continue
            for xs in xs_set:
                if xs == gn or (len(gn) >= 4 and (xs.startswith(gn) or gn.startswith(xs))):
                    xs_in_gold.add(xs)
    xs_extras = {n for n in xs_set if n not in xs_in_gold}

    # Map extras back to original core_names for readability
    xs_original = {ev["core_name"] for ev in ev_db.get("evidence", [])}
    xs_extras_named = sorted(
        {orig for orig in xs_original
         if _eval_normalize(orig, alias_map) in xs_extras}
    )

    # Metrics
    n_gold = len(gold["candidates"])
    n_hit = len(gold_hit)
    recall = n_hit / n_gold if n_gold else 0.0
    n_xs = len(xs_set)
    # Precision = xscreen entries also in gold / total xscreen entries.
    # Note: extras are not necessarily *wrong* (novel valid candidates), so
    # precision here is "fraction overlapping curated gold", not "correctness".
    precision = len(xs_in_gold) / n_xs if n_xs else 0.0
    f1 = (2 * recall * precision / (recall + precision)) if (recall + precision) else 0.0

    return {
        "n_gold": n_gold,
        "n_xscreen": n_xs,
        "n_hit": n_hit,
        "n_extras": len(xs_extras),
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "tiers": {t: {"total": len(tiers[t]),
                       "hit": sum(1 for e in tiers[t] if e["matched"]),
                       "miss": [e["name"] for e in tiers[t] if not e["matched"]]}
                  for t in tiers},
        "gold_miss": [e["name"] for e in gold_miss],
        "xscreen_extras": xs_extras_named,
    }


def render_report(result: dict) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("xscreen vs Gold Standard Evaluation")
    lines.append("=" * 72)
    lines.append("")
    lines.append("## Overall Metrics")
    lines.append(f"  Gold candidates   : {result['n_gold']}")
    lines.append(f"  xscreen extracted : {result['n_xscreen']}")
    lines.append(f"  Hits (gold ∩ xs)  : {result['n_hit']}")
    lines.append(f"  Extras (xs only)  : {result['n_extras']}")
    lines.append("")
    lines.append(f"  Recall    : {result['recall']:.3f}  ({result['n_hit']}/{result['n_gold']})")
    lines.append(f"  Precision : {result['precision']:.3f}  (overlap with curated gold)")
    lines.append(f"  F1        : {result['f1']:.3f}")
    lines.append("")
    lines.append("## Recall by relevance tier")
    for tier in ("high", "medium", "low"):
        t = result["tiers"][tier]
        r = t["hit"] / t["total"] if t["total"] else 0.0
        lines.append(f"  {tier:<8} {t['hit']}/{t['total']} = {r:.2f}")
        if t["miss"]:
            lines.append(f"           missed: {', '.join(t['miss'])}")
    lines.append("")
    lines.append("## xscreen extras (not in gold)")
    extras = result["xscreen_extras"]
    if extras:
        for e in extras:
            lines.append(f"  - {e}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("=" * 72)
    report = "\n".join(lines)
    print(report)
    return report


def main(config_path: str) -> int:
    config = load_config(config_path)
    output_dir = get_output_dir(config, config_path)
    case_dir = Path(config_path).parent

    # Locate gold standard: prefer case-local, fall back to nothing.
    gold_path = case_dir / "gold_standard.json"
    ev_path = output_dir / config["output"]["database"]

    if not gold_path.exists():
        print(f"ERROR: gold standard not found at {gold_path}")
        return 2
    if not ev_path.exists():
        print(f"ERROR: evidence db not found at {ev_path}")
        print("Run the pipeline first: python src/run.py <config>")
        return 2

    # Build alias map for bilateral normalization (merge synonyms to canonical)
    alias_map = _build_eval_alias_map(config, case_dir)

    result = evaluate(gold_path, ev_path, alias_map=alias_map)
    render_report(result)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m tools.eval_vs_gold <config.yaml>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
