"""Tests for src/type_filter.py — type_error 检测（receptor/enzyme/drug/metabolite/noise）。

验证三类：
1. 各 is_* 函数代表性样本（单元测试）
2. is_type_error 聚合 + KNOWN_AMINES 白名单（修复 5-HT 被 is_noise 误判的 bug）
3. 全量回归（数据驱动，从 uniprot_validation.json 加载，skip if 文件不存在）
"""
import json
from pathlib import Path

import pytest

from src.type_filter import (
    is_receptor, is_enzyme, is_drug, is_metabolite, is_noise,
    is_type_error, KNOWN_AMINES,
)

PROJECT_ROOT = Path(__file__).parent.parent
UNIPROT_JSON = (PROJECT_ROOT / "cases/locust_sih/output_unbiased"
                / "uniprot_validation.json")


# ---------------------------------------------------------------------------
# 1. is_receptor
# ---------------------------------------------------------------------------
class TestIsReceptor:
    @pytest.mark.parametrize("name", [
        "NPF receptor", "dopamine receptor", "AKHR", "NPFR", "sNPFR",
        "5-HT2A", "5-HT1A", "5HT1AR", "Dop1R1", "D2R", "CCHa2-R", "PDFR",
    ])
    def test_receptor(self, name):
        assert is_receptor(name), f"{name} 应被识别为受体"

    @pytest.mark.parametrize("name", [
        "NPF", "AKH", "sNPF", "dopamine", "5-HT", "5-HTP", "PDF",
    ])
    def test_not_receptor(self, name):
        assert not is_receptor(name), f"{name} 不是受体"


# ---------------------------------------------------------------------------
# 2. is_enzyme / is_drug / is_metabolite / is_noise
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["ACE", "TH"])
def test_is_enzyme(name):
    assert is_enzyme(name)


@pytest.mark.parametrize("name", ["NPF", "AKH", "dopamine"])
def test_not_enzyme(name):
    assert not is_enzyme(name)


@pytest.mark.parametrize("name", ["chlorpromazine", "flupenthixol", "ketanserin"])
def test_is_drug(name):
    assert is_drug(name)


@pytest.mark.parametrize("name", ["ATP", "cAMP", "trehalose"])
def test_is_metabolite(name):
    assert is_metabolite(name)


def test_is_noise_sequence_fragment():
    assert is_noise("2129-SP3[Phi3]wp-2")
    assert is_noise("CG1234")


# ---------------------------------------------------------------------------
# 3. is_type_error 聚合 + KNOWN_AMINES 白名单
# ---------------------------------------------------------------------------
class TestIsTypeError:
    def test_5HT_whitelist_fix(self):
        """5-HT/5-HTP 以数字开头+连字符，匹配 is_noise 的碎片规则，
        但 KNOWN_AMINES 白名单优先——杠杆 2 修复的已知 bug。"""
        assert not is_type_error("5-HT")
        assert not is_type_error("5-HTP")

    @pytest.mark.parametrize("name", sorted(KNOWN_AMINES))
    def test_all_known_amines_whitelisted(self, name):
        assert not is_type_error(name), f"胺 {name} 被误判为 type_error"

    @pytest.mark.parametrize("name", [
        "NPF", "sNPF", "AKH", "PDF", "dopamine", "octopamine", "serotonin",
        "tyramine", "FMRFamide", "sulfakinin", "allatostatin", "corazonin",
        "ITP", "allatotropin", "tachykinin", "leucokinin",
    ])
    def test_core_peptides_not_type_error(self, name):
        """核心真肽不被误判——辅助筛选的锚点必须保留。"""
        assert not is_type_error(name), f"核心肽 {name} 误判为 type_error！"

    @pytest.mark.parametrize("name", [
        "AKHR", "5-HT2A", "NPF receptor", "ACE", "TH",
        "chlorpromazine", "ATP", "cAMP", "CG1234",
    ])
    def test_type_errors_flagged(self, name):
        assert is_type_error(name), f"{name} 应被识别为 type_error"


# ---------------------------------------------------------------------------
# 4. 全量回归（数据驱动，从 uniprot_validation.json 加载）
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not UNIPROT_JSON.exists(),
                    reason="uniprot_validation.json 不存在，跳过全量回归")
class TestFullRegression:
    """从 uniprot_validation.json 加载全量 type_error，验证 is_type_error 全命中。

    这是回归保护：确保 src/type_filter.py 的规则覆盖所有已知 type_error，
    不会因重构漏掉某一类（如漏掉 Dop1R1 模式）。
    """

    @pytest.fixture(scope="class")
    def classification(self):
        data = json.loads(UNIPROT_JSON.read_text(encoding="utf-8"))
        return data["classification"]

    def test_all_receptors_detected(self, classification):
        names = classification.get("receptor", [])
        # 杠杆 2 后候选池缩小（517→389），receptor 63→19；下限设 10 防空载。
        assert len(names) >= 10, f"receptor 候选数异常: {len(names)}"
        misses = [n for n in names if not is_type_error(n)]
        assert misses == [], f"未识别的 receptor: {misses}"

    def test_all_enzymes_detected(self, classification):
        misses = [n for n in classification.get("enzyme", [])
                  if not is_type_error(n)]
        assert misses == [], f"未识别的 enzyme: {misses}"

    def test_all_drugs_detected(self, classification):
        misses = [n for n in classification.get("drug", [])
                  if not is_type_error(n)]
        assert misses == [], f"未识别的 drug: {misses}"

    def test_all_metabolites_detected(self, classification):
        misses = [n for n in classification.get("metabolite", [])
                  if not is_type_error(n)]
        assert misses == [], f"未识别的 metabolite: {misses}"

    def test_noise_except_whitelisted_amines(self, classification):
        """noise 类别：白名单胺（5-HT 旧 is_noise 误判）外全命中。
        白名单胺反而是修复验证——它们不应被 is_type_error 标记。"""
        for n in classification.get("noise", []):
            if n.upper() in {a.upper() for a in KNOWN_AMINES}:
                assert not is_type_error(n), f"白名单胺 {n} 被误判"
            else:
                assert is_type_error(n), f"未识别的 noise: {n}"
