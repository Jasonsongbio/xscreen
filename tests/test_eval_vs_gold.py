"""Tests for tools/eval_vs_gold.py — 双边规范化 eval 匹配。

验证：
1. 有 alias_map 时 "AT"（gold）~"Allatotropin"（xscreen）匹配命中
2. 无 alias_map（None）时降级到原 prefix 匹配，不崩
3. -like 变体经 normalize_core_name 后也能匹配
4. 无关候选不误匹配
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.normalize import build_alias_map
from tools.eval_vs_gold import evaluate, _build_eval_alias_map, _eval_normalize


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mini_alias_map():
    """小型 alias_map：Allatotropin aliases=["AT"]。"""
    master = {
        "Allatotropin": {"category": "peptide", "aliases": ["AT"]},
        "NPF": {"category": "peptide", "aliases": ["Neuropeptide F"]},
    }
    return build_alias_map(master)


@pytest.fixture
def mini_gold(tmp_path):
    """Mini gold standard：含 "AT"（带 alias allatotropin）。"""
    gold = {
        "candidates": [
            {
                "name": "AT",
                "aliases": ["allatotropin"],
                "relevance": "high",
                "in_reviews": 3,
            },
            {
                "name": "NPF",
                "aliases": ["Neuropeptide F"],
                "relevance": "medium",
                "in_reviews": 2,
            },
        ]
    }
    path = tmp_path / "gold_standard.json"
    path.write_text(json.dumps(gold), encoding="utf-8")
    return path


@pytest.fixture
def mini_evidence_db(tmp_path):
    """Mini evidence_db：core_name="Allatotropin" 和 "allatotropin-like" 和 "NPF"。"""
    ev_db = {
        "evidence": [
            {"core_name": "Allatotropin", "study": "paper1"},
            {"core_name": "allatotropin-like", "study": "paper2"},
            {"core_name": "NPF", "study": "paper3"},
        ]
    }
    path = tmp_path / "evidence_db.json"
    path.write_text(json.dumps(ev_db), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. 双边 normalize 匹配
# ---------------------------------------------------------------------------
class TestBilateralNormalize:
    def test_at_matches_allatotropin(self, mini_gold, mini_evidence_db, mini_alias_map):
        """有 alias_map 时 gold "AT" 规范化到 "Allatotropin"，匹配 xscreen "Allatotropin"。"""
        result = evaluate(mini_gold, mini_evidence_db, alias_map=mini_alias_map)
        assert result["n_hit"] >= 1
        # AT 应在 gold_hit 里（不在 miss 里）
        assert "AT" not in result["gold_miss"]
        assert result["recall"] > 0.0

    def test_like_variant_matched(self, mini_gold, mini_evidence_db, mini_alias_map):
        """allatotropin-like 经 normalize_core_name 后也合并到 Allatotropin。"""
        result = evaluate(mini_gold, mini_evidence_db, alias_map=mini_alias_map)
        # Allatotropin 和 allatotropin-like 都规范化为 Allatotropin，
        # 在 xs_set 里是一个 key，不会产生 extras
        assert "allatotropin-like" not in result["xscreen_extras"]
        assert "Allatotropin" not in result["xscreen_extras"]

    def test_npf_matched(self, mini_gold, mini_evidence_db, mini_alias_map):
        """NPF 在 gold 和 xscreen 都有，应该匹配。"""
        result = evaluate(mini_gold, mini_evidence_db, alias_map=mini_alias_map)
        assert "NPF" not in result["gold_miss"]


# ---------------------------------------------------------------------------
# 2. 无 alias_map 降级（不崩 + 原行为）
# ---------------------------------------------------------------------------
class TestNoAliasMap:
    def test_none_alias_map_no_crash(self, mini_gold, mini_evidence_db):
        """alias_map=None 不应崩溃。"""
        result = evaluate(mini_gold, mini_evidence_db, alias_map=None)
        assert "recall" in result
        assert "precision" in result

    def test_none_alias_map_prefix_match(self, mini_gold, mini_evidence_db):
        """无 alias_map 时 "AT" 仍可通过 gold aliases=["allatotropin"] 做 prefix 匹配。

        gold 的 alias "allatotropin" -> _normalize -> "allatotropin"
        xscreen "Allatotropin" -> _normalize -> "allatotropin"
        所以即使无 normalize_core_name 也能匹配（prefix exact）。
        """
        result = evaluate(mini_gold, mini_evidence_db, alias_map=None)
        # "AT" 在 gold 里有 alias "allatotropin"，xscreen 有 "Allatotropin"
        # _normalize 后都是 "allatotropin"，所以能匹配
        assert "AT" not in result["gold_miss"]


# ---------------------------------------------------------------------------
# 3. _eval_normalize 单元测试
# ---------------------------------------------------------------------------
class TestEvalNormalize:
    def test_with_alias_map(self, mini_alias_map):
        """有 alias_map 时先规范化再 _normalize。"""
        result = _eval_normalize("AT", mini_alias_map)
        # AT -> normalize_core_name -> "Allatotropin" -> _normalize -> "allatotropin"
        assert result == "allatotropin"

    def test_without_alias_map(self):
        """无 alias_map 时纯 _normalize。"""
        result = _eval_normalize("AT", None)
        assert result == "at"

    def test_like_variant_normalized(self, mini_alias_map):
        """allatotropin-like -> Allatotropin -> allatotropin。"""
        result = _eval_normalize("allatotropin-like", mini_alias_map)
        assert result == "allatotropin"


# ---------------------------------------------------------------------------
# 4. _build_eval_alias_map 降级逻辑
# ---------------------------------------------------------------------------
class TestBuildEvalAliasMap:
    def test_no_master_list_returns_none(self):
        """config 无 master_list 时返回 None。"""
        config = {"study": {}}
        result = _build_eval_alias_map(config, Path("."))
        assert result is None

    def test_nonexistent_master_list_returns_none(self, tmp_path):
        """master_list 文件不存在时返回 None。"""
        config = {"study": {"master_list": "nonexistent.md"}}
        result = _build_eval_alias_map(config, tmp_path)
        assert result is None

    def test_loads_real_master_list(self):
        """有真实主表时返回非空 alias_map（集成测试）。"""
        project_root = Path(__file__).parent.parent
        master = project_root / "cases/locust_sih/neuropeptide_master_list.md"
        if not master.exists():
            pytest.skip("主表不存在")
        config = {"study": {"master_list": "cases/locust_sih/neuropeptide_master_list.md"}}
        result = _build_eval_alias_map(config, project_root)
        assert result is not None
        assert len(result) > 0
