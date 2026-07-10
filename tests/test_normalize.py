"""Tests for src/normalize.py — core_name 规范化（合并同义词变体）。

验证：
1. _norm / _is_valid_alias 基础函数
2. build_alias_map 构建 + 噪声过滤
3. normalize_core_name 4 条规则（精确/物种前缀/-like/-amide）
4. 不误合并（保守性：ACE/dopamine/NPF/CCHa-2）
5. 全量主表集成（真实数据，skip if 主表不存在）
"""
import sys
from pathlib import Path

import pytest

from src.normalize import (
    _norm, _is_valid_alias, build_alias_map, normalize_core_name,
)

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_PATH = PROJECT_ROOT / "cases/locust_sih/neuropeptide_master_list.md"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def small_alias_map():
    """小型 alias_map 用于规则单元测试（隔离，不依赖主表文件）。"""
    master = {
        "Allatotropin": {"category": "peptide", "aliases": ["AT"]},
        "FMRFamide": {"category": "peptide", "aliases": ["—"]},
        "SIFamide": {"category": "peptide", "aliases": ["SIFa"]},
        "Tachykinin": {"category": "peptide", "aliases": ["DTK"]},
        "NPLP1": {"category": "peptide", "aliases": ["Neuropeptide-like precursor 1"]},
        "NPF": {"category": "peptide", "aliases": ["Neuropeptide F"]},
    }
    return build_alias_map(master)


# ---------------------------------------------------------------------------
# 1. _norm / _is_valid_alias
# ---------------------------------------------------------------------------
class TestNorm:
    def test_norm_lowercase_strip(self):
        assert _norm("AT") == "at"
        assert _norm("Allatotropin") == "allatotropin"
        assert _norm("Mas-allatotropin") == "masallatotropin"
        assert _norm("Neuropeptide F") == "neuropeptidef"
        assert _norm("**OEH**") == "oeh"

    def test_is_valid_alias_filters_noise(self):
        assert _is_valid_alias("AT")
        assert _is_valid_alias("Neuropeptide F")
        assert not _is_valid_alias("—")
        assert not _is_valid_alias("")
        assert not _is_valid_alias("运动、奖赏、睡眠")  # 中文功能描述混入
        assert not _is_valid_alias("x" * 30)  # 太长


# ---------------------------------------------------------------------------
# 2. build_alias_map
# ---------------------------------------------------------------------------
class TestBuildAliasMap:
    def test_canonical_and_alias_mapped(self, small_alias_map):
        assert small_alias_map["at"] == "Allatotropin"
        assert small_alias_map["allatotropin"] == "Allatotropin"
        assert small_alias_map["sifamide"] == "SIFamide"
        assert small_alias_map["sifa"] == "SIFamide"

    def test_dash_alias_filtered(self, small_alias_map):
        """FMRFamide aliases=['—'] 应被过滤，不进 alias_map。"""
        assert _norm("—") not in small_alias_map
        assert small_alias_map["fmrfamide"] == "FMRFamide"  # canonical 本身在


# ---------------------------------------------------------------------------
# 3. normalize_core_name 4 规则
# ---------------------------------------------------------------------------
class TestNormalizeRules:
    def test_rule1_exact_match(self, small_alias_map):
        assert normalize_core_name("AT", small_alias_map) == "Allatotropin"
        assert normalize_core_name("allatotropin", small_alias_map) == "Allatotropin"
        assert normalize_core_name("DTK", small_alias_map) == "Tachykinin"
        assert normalize_core_name("SIFa", small_alias_map) == "SIFamide"

    def test_rule2_species_prefix_strip(self, small_alias_map):
        assert normalize_core_name("Mas-allatotropin", small_alias_map) == "Allatotropin"
        assert normalize_core_name("Lom-allatotropin", small_alias_map) == "Allatotropin"

    def test_rule3_like_suffix_strip(self, small_alias_map):
        assert normalize_core_name("allatotropin-like", small_alias_map) == "Allatotropin"

    def test_rule4_a_to_amide(self, small_alias_map):
        """FMRFa → FMRFamide（FMRFa 不在 alias_map，但 -a→-amide 规则命中）。"""
        assert normalize_core_name("FMRFa", small_alias_map) == "FMRFamide"

    def test_case_insensitive(self, small_alias_map):
        assert normalize_core_name("nplp1", small_alias_map) == "NPLP1"
        assert normalize_core_name("Nplp1", small_alias_map) == "NPLP1"

    def test_rule5_parentheses_plural(self, small_alias_map):
        """规则5：括号内容清理 + 复数剥离（泛称变体合并）。

        "Allatotropins (ATs)" -> 去括号 "Allatotropins" -> 去复数
        "Allatotropin" -> 匹配主表 canonical。仅当清理后能匹配时采用。
        """
        assert normalize_core_name("Allatotropins (ATs)", small_alias_map) == "Allatotropin"
        assert normalize_core_name("FMRFamides", small_alias_map) == "FMRFamide"

    def test_rule5_no_false_merge(self, small_alias_map):
        """规则5 保守：清理后不匹配主表则返回原名，短名(<5)不触发复数剥离。"""
        # 不匹配主表 -> 原名（不误合并）
        assert normalize_core_name("calciums", small_alias_map) == "calciums"
        # 短名 ATs (len 3 < 5) 不剥复数 -> 原名
        assert normalize_core_name("ATs", small_alias_map) == "ATs"
        # 去括号后仍不匹配 -> 原名
        assert normalize_core_name("UnknownPeptide (x)", small_alias_map) == "UnknownPeptide (x)"


# ---------------------------------------------------------------------------
# 4. 不误合并（保守性验证 —— 最重要）
# ---------------------------------------------------------------------------
class TestNoFalseMerge:
    def test_known_amines_whitelist(self, small_alias_map):
        """已知胺绝不被规则改写（即使以 a/A 结尾如 GABA）。"""
        for amine in ["dopamine", "serotonin", "octopamine", "5-HT",
                      "GABA", "tyramine", "histamine"]:
            assert normalize_core_name(amine, small_alias_map) == amine

    def test_enzyme_not_merged(self, small_alias_map):
        """ACE（酶）不在主表肽 alias，返回原名。"""
        assert normalize_core_name("ACE", small_alias_map) == "ACE"

    def test_unmapped_returns_original(self, small_alias_map):
        assert normalize_core_name("UnknownPeptide", small_alias_map) == "UnknownPeptide"
        assert normalize_core_name("NPF", small_alias_map) == "NPF"

    def test_species_prefix_not_overstripped(self, small_alias_map):
        """CCHa-2 / AKH-I 不应被误剥离（正则要求 ^[A-Z][a-z]{1,4}- 格式）。

        CCHa 含大写 H，AKH 全大写，都不匹配物种前缀正则。
        """
        assert normalize_core_name("CCHa-2", small_alias_map) == "CCHa-2"
        assert normalize_core_name("AKH-I", small_alias_map) == "AKH-I"

    def test_empty_map_passthrough(self):
        """alias_map 为空 dict 时返回原名（兜底）。"""
        assert normalize_core_name("AT", {}) == "AT"


# ---------------------------------------------------------------------------
# 5. 全量主表集成（真实数据）
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not MASTER_PATH.exists(), reason="主表不存在")
class TestFullMasterIntegration:
    @pytest.fixture(scope="class")
    def full_alias_map(self):
        sys.path.insert(0, str(PROJECT_ROOT))
        from tools.coverage_check import load_master_list
        master = load_master_list(str(MASTER_PATH))
        target = {k: v for k, v in master.items()
                  if v["category"] not in ("off_topic", "exclude")}
        return build_alias_map(target)

    def test_allatotropin_variants_merge(self, full_alias_map):
        """所有 allatotropin 变体合并到 Allatotropin（修复目标）。"""
        for variant in ["AT", "allatotropin", "Mas-allatotropin",
                        "allatotropin-like"]:
            result = normalize_core_name(variant, full_alias_map)
            assert result == "Allatotropin", f"{variant} -> {result}"

    def test_core_peptides_stable(self, full_alias_map):
        """核心肽规范化后稳定（不误改）。"""
        for name in ["NPF", "AKH", "dopamine", "sNPF", "PDF", "octopamine"]:
            assert normalize_core_name(name, full_alias_map) == name
