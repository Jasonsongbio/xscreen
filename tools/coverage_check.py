"""Coverage check（策略 B 核心）

对比「策略 A 浮上来的候选」vs「已知昆虫神经肽全表」：
- 策略 A（query-driven）从 1349 篇无偏 corpus 浮上来的候选
- 策略 B（candidate-enumeration）从 neuropeptide_master_list.md 枚举的全表

输出：
1. 覆盖率：全表中多少肽被策略 A 命中
2. 遗漏肽：哪些已知肽没被策略 A 浮上来（需策略 B 补全）
3. 新发现：策略 A 浮上来但不在全表的（潜在新候选或命名差异）

这是双策略方法学的核心：A 保证发现能力，B 保证覆盖率兜底。

用法：
    python tools/coverage_check.py
"""
import sys
import json
import re
from pathlib import Path
from rapidfuzz import fuzz

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_master_list(md_path: str) -> dict[str, dict]:
    """从 neuropeptide_master_list.md 解析已知肽全表。

    返回 {canonical_name: {aliases: [...], category: ..., function: ...}}
    """
    text = open(md_path, encoding="utf-8").read()
    entries = {}
    # 匹配表格行：| # | 名称 | 别名 | 功能 | ... |
    # 简化解析：抓所有表格行中第 2 列（名称）
    lines = text.split("\n")
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]  # 去空
        if len(cells) < 3:
            continue
        # 第一列应该是数字（序号）
        if not cells[0].isdigit():
            continue
        idx, name = cells[0], cells[1]
        # 跳过分隔行 / 标题行
        if name in ("名称", "Name", "---", "名称/亚型"):
            continue
        aliases = cells[2] if len(cells) > 2 else ""
        # 清理别名（去掉 markdown 格式）
        aliases_clean = re.sub(r"[*_`]", "", aliases)
        alias_list = [a.strip() for a in re.split(r"[/,，]", aliases_clean) if a.strip()]
        function = cells[3] if len(cells) > 3 else ""
        category = _infer_category(idx, text, line)
        entries[name] = {
            "aliases": alias_list,
            "function": re.sub(r"[*_`]", "", function),
            "category": category,
        }
    return entries


def _infer_category(idx: str, full_text: str, line: str) -> str:
    """根据 markdown 章节标题推断类别。简化版：查 line 前最近的 ## 标题。"""
    # 找当前行在全文的行号
    target = line
    for i, l in enumerate(full_text.split("\n")):
        if l == target:
            # 往前找最近的 ## 标题
            for j in range(i, -1, -1):
                prev = full_text.split("\n")[j]
                if prev.startswith("## "):
                    heading = prev[3:].strip()
                    if "胺" in heading or "Amine" in heading:
                        return "amine"
                    if "递质" in heading or "Neurotransmitter" in heading:
                        return "neurotransmitter"
                    if "排除" in heading or "OUT" in heading:
                        return "exclude"
                    if "哺乳" in heading or "off_topic" in heading:
                        return "off_topic"
                    return "peptide"
            break
    return "peptide"


def normalize_name(name: str) -> str:
    """标准化名称用于匹配：大写、去空格/连字符/数字后缀。"""
    n = name.upper().strip()
    # 去常见后缀变体：NPF1a -> NPF, AKH-I -> AKH
    n = re.sub(r"[-\s]", "", n)
    # 保留：NPF, AKH, DOPAMINE, OCTOPAMINE
    return n


def fuzzy_match(candidate: str, master_entries: dict, threshold: float = 85.0) -> str | None:
    """模糊匹配 candidate 到 master 全表。

    先精确（normalize 后），再 fuzzy（partial_ratio）。
    返回匹配的 canonical name 或 None。
    """
    cand_norm = normalize_name(candidate)

    # 1. 精确匹配（normalize 后）
    for master_name, info in master_entries.items():
        if normalize_name(master_name) == cand_norm:
            return master_name
        # 别名匹配
        for alias in info["aliases"]:
            if normalize_name(alias) == cand_norm:
                return master_name

    # 2. 子串匹配（NPF 匹配 NPF1a / NPF1 / NPF2 等）
    for master_name, info in master_entries.items():
        m_norm = normalize_name(master_name)
        if len(cand_norm) >= 3 and cand_norm in m_norm:
            return master_name
        if len(m_norm) >= 3 and m_norm in cand_norm:
            return master_name
        for alias in info["aliases"]:
            a_norm = normalize_name(alias)
            if len(a_norm) >= 3 and a_norm in cand_norm:
                return master_name

    # 3. fuzzy 匹配（partial_ratio）
    best_score = 0
    best_match = None
    for master_name, info in master_entries.items():
        score = fuzz.partial_ratio(cand_norm, normalize_name(master_name))
        if score > best_score:
            best_score = score
            best_match = master_name
        for alias in info["aliases"]:
            score = fuzz.partial_ratio(cand_norm, normalize_name(alias))
            if score > best_score:
                best_score = score
                best_match = master_name

    return best_match if best_score >= threshold else None


def main():
    master_path = PROJECT_ROOT / "cases/locust_sih/neuropeptide_master_list.md"
    unbiased_db = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"
    # report.py 输出的 evidence_db.json（score 后）
    scored_db = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"

    # 哪个 db 存在就用哪个（score 后的更准，extract 后的也有候选列表）
    db_path = scored_db if scored_db.exists() else unbiased_db
    if not db_path.exists():
        print(f"ERROR: {db_path} 不存在，先跑 extract + score")
        sys.exit(1)

    print(f"=== Coverage Check（策略 B）===")
    print(f"主表: {master_path.name}")
    print(f"候选来源: {db_path.name}")

    # 加载主表
    master = load_master_list(str(master_path))
    print(f"主表已知肽数: {len(master)}")

    # 过滤 off_topic / exclude（只检查目标候选）
    target_master = {
        k: v for k, v in master.items()
        if v["category"] not in ("off_topic", "exclude")
    }
    print(f"目标候选范围（去 off_topic/exclude）: {len(target_master)}")

    # 加载策略 A 候选
    data = json.load(open(db_path, encoding="utf-8"))
    # 用 evidence 字段提取全部候选（core_name 去重），不是 ranked top_n
    # 因为 coverage check 的目的是"全表里的肽哪些被策略 A 发现"，不限排名
    if "evidence" in data:
        strategy_a_cands = {ev["core_name"] for ev in data["evidence"] if ev.get("core_name")}
    elif "candidates" in data:
        strategy_a_cands = {c["candidate"] for c in data["candidates"]}
    else:
        strategy_a_cands = {c[0] for c in data.get("top_candidates", [])}
    print(f"策略 A 浮上来候选数（全部 evidence 去重）: {len(strategy_a_cands)}")

    # 匹配
    covered = {}  # master_name -> [matched strategy_a candidates]
    uncovered = []  # master_name 没被命中
    new_discoveries = []  # strategy_a 候选没匹配上 master

    for m_name in target_master:
        matches = []
        for c in strategy_a_cands:
            matched = fuzzy_match(c, {m_name: target_master[m_name]})
            if matched:
                matches.append(c)
        if matches:
            covered[m_name] = matches
        else:
            uncovered.append(m_name)

    for c in strategy_a_cands:
        matched = fuzzy_match(c, target_master)
        if not matched:
            new_discoveries.append(c)

    # 报告
    coverage_rate = len(covered) / len(target_master) * 100 if target_master else 0
    print(f"\n=== 覆盖率 ===")
    print(f"策略 A 命中: {len(covered)}/{len(target_master)} = {coverage_rate:.1f}%")
    print(f"遗漏（需策略 B 补全）: {len(uncovered)}")

    print(f"\n=== 遗漏的已知肽（策略 A 没浮上来）===")
    # 按类别分组
    by_cat = {}
    for m in uncovered:
        cat = target_master[m]["category"]
        by_cat.setdefault(cat, []).append(m)
    for cat, names in sorted(by_cat.items()):
        print(f"  [{cat}] ({len(names)}):")
        for n in names:
            func = target_master[n]["function"][:40]
            print(f"    - {n}: {func}")

    print(f"\n=== 策略 A 新发现（不在主表）===")
    print(f"数量: {len(new_discoveries)}")
    for c in sorted(new_discoveries)[:20]:
        print(f"  - {c}")

    # 保存
    out_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/coverage_check.json"
    out_data = {
        "master_list_size": len(master),
        "target_candidates_size": len(target_master),
        "strategy_a_candidates_size": len(strategy_a_cands),
        "covered": {k: v for k, v in covered.items()},
        "uncovered": uncovered,
        "new_discoveries": new_discoveries,
        "coverage_rate": coverage_rate,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 结果保存到 {out_path}")


if __name__ == "__main__":
    main()
