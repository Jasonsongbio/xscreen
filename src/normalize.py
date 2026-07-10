"""core_name 规范化：把同一肽的不同命名变体合并到主表 canonical 名。

xscreen 的 score.py 按 core_name 分组 evidence。LLM 对同一肽可能输出不同
core_name（缩写 vs 全称 vs 物种前缀变体 vs -like 变体），导致同一肽的 evidence
被拆分到多个弱候选。本模块在 score 分组前把 core_name 规范化到统一名。

**保守原则：每个规则只有"结果能匹配主表 canonical"时才采用，否则返回原名。**
不做模糊子串匹配（避免 ACE/acetylcholine 假阳性）。

规则优先级：
0. KNOWN_AMINES 白名单优先（dopamine/5-HT 等不动）
1. 精确匹配主表 alias（大小写/连字符/空格不敏感）
2. 物种前缀剥离（Mas-/Lom-/Dm- 等物种缩写）后重试
3. -like / -related 后缀剥离后重试
4. -a ↔ -amide 互换（FMRFa → FMRFamide）后重试
5. 未命中：返回原名（绝不乱合并）
"""
import re

from .type_filter import KNOWN_AMINES


def _norm(s: str) -> str:
    """规范化字符串用于匹配键：小写 + 去 markdown 标记/连字符/空格。"""
    s = s.strip().lower()
    s = s.replace("*", "").replace("_", "")  # markdown bold/italic（如 **OEH**）
    s = re.sub(r"[-\s]", "", s)  # 连字符和空格
    return s


def _is_valid_alias(s: str) -> bool:
    """判断主表 alias 字段是否是合法别名（过滤噪声）。

    主表 load_master_list 的 aliases 有时混入功能描述（如 dopamine 的
    ['运动、奖赏、睡眠']）或占位破折号（['—']）。这些不是真 alias。
    """
    if not s:
        return False
    s = s.strip()
    if s in ("—", "-", ""):
        return False
    if len(s) > 25:  # 真正的 alias 不会太长
        return False
    # 含中文 = 功能描述混入（主表胺类表格列错位）
    if any("\u4e00" <= c <= "\u9fff" for c in s):
        return False
    return True


def build_alias_map(master: dict) -> dict[str, str]:
    """从主表构建 normalized_alias -> canonical 映射。

    Args:
        master: {name: {category, aliases, ...}}，应已过滤 off_topic/exclude。

    Returns:
        {normalized_alias_key: canonical_name}。canonical 名本身也加入。
    """
    alias_map: dict[str, str] = {}
    for name, info in master.items():
        # canonical 名本身（即使 aliases 为空，canonical 也作为 key）
        names = [name]
        for a in info.get("aliases", []):
            if _is_valid_alias(a):
                names.append(a)
        for nm in names:
            if not _is_valid_alias(nm):
                continue
            key = _norm(nm)
            if key and key not in alias_map:  # 首次出现的 canonical 优先
                alias_map[key] = name
    return alias_map


def normalize_core_name(name: str, alias_map: dict[str, str]) -> str:
    """规范化 core_name 到主表 canonical 名（保守，未命中返回原名）。

    Args:
        name: LLM 输出的 core_name。
        alias_map: build_alias_map 的结果。

    Returns:
        规范化后的 canonical 名，或原名（无法匹配时）。
    """
    if not name:
        return name

    # 0. 已知胺白名单优先（dopamine/5-HT/GABA 等绝不动）
    if name.strip().upper() in {a.upper() for a in KNOWN_AMINES}:
        return name

    # 1. 精确匹配（大小写/连字符/空格不敏感）
    hit = alias_map.get(_norm(name))
    if hit:
        return hit

    # 2. 物种前缀剥离（Mas-/Lom-/Dm- 等物种缩写，如 Mas-allatotropin）
    # 正则要求：首字母大写 + 1-4 小写 + 连字符。CCHa-/AKH- 不匹配（含大写/全大写）。
    stripped = re.sub(r"^[A-Z][a-z]{1,4}-", "", name)
    if stripped != name:
        hit = alias_map.get(_norm(stripped))
        if hit:
            return hit

    # 3. -like / -related 后缀剥离（allatotropin-like -> allatotropin）
    low = name.lower()
    for suffix in ("-like", "-related"):
        if low.endswith(suffix):
            base = name[: -len(suffix)]
            hit = alias_map.get(_norm(base))
            if hit:
                return hit

    # 4. -a ↔ -amide 互换（FMRFa -> FMRFamide）
    # 仅当以单字母 'a' 结尾且替换后能匹配主表时采用。
    # 胺类已被规则 0 白名单保护，不会误入。
    if name.endswith("a") and len(name) >= 4:
        candidate = name[:-1] + "amide"
        hit = alias_map.get(_norm(candidate))
        if hit:
            return hit

    # 5. 括号内容清理 + 复数后缀剥离后重试
    # 处理 "Allatostatins (ASTs)" / "neuropeptides (NPs)" 等泛称变体。
    # 保守：仅当清理后能匹配主表 canonical 时采用。复数剥离要求 len>=5
    # 避免 "ATs"->"AT" 这类误触发（短名已在规则1精确匹配）。
    cleaned = re.sub(r"\(.*?\)", "", name).strip()
    if cleaned.endswith("s") and len(cleaned) >= 5:
        cleaned = cleaned[:-1]  # 去复数 -s
    if cleaned and _norm(cleaned) != _norm(name):
        hit = alias_map.get(_norm(cleaned))
        if hit:
            return hit

    # 6. 未命中：保守返回原名
    return name
