"""无偏 corpus LLM extraction（策略 A）

从 cases/locust_sih/unbiased_papers.json 加载论文，跑 review-aware 双路径
extraction，输出 evidence_db.json 到 output_unbiased/。

用法：
    # smoke test（20 篇）
    python tools/extract_unbiased.py cases/locust_sih/config_unbiased.yaml --limit 20

    # 全量（1349 篇，8 并发）
    python tools/extract_unbiased.py cases/locust_sih/config_unbiased.yaml

设计要点：
    - 绕过 search/screen 模块（unbiased corpus 已由 fetch_unbiased_corpus.py 收集）
    - 直接调用 extract.extract_evidence() 单篇函数，自己控制循环 + 并发
    - paper_type 从 PubMed publication_types 推断（含 "Review" → review 路径）
    - token 消耗追踪（包装 LLMClient 计数）
"""
import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 项目根目录加入 sys.path（让 src 可导入）
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402
from src.search import Paper  # noqa: E402
from src.extract import extract_evidence, load_prompt, _make_llm_client  # noqa: E402
from src.llm_client import LLMClient  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("extract_unbiased")


def load_env(path: str = ".env") -> None:
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v


def load_papers_from_json(json_path: str, limit: int | None = None) -> list[Paper]:
    """从 unbiased_papers.json 加载论文 → list[Paper]。

    paper_type 推断：publication_types 含 "Review" → "review"，否则 "primary"。
    """
    data = json.load(open(json_path, encoding="utf-8"))
    raw_papers = data["papers"]
    if limit:
        raw_papers = raw_papers[:limit]

    papers: list[Paper] = []
    for p in raw_papers:
        pub_types = p.get("publication_types", [])
        paper_type = "review" if any("Review" in pt for pt in pub_types) else "primary"
        papers.append(
            Paper(
                id=p["id"],
                source="pubmed",
                title=p.get("title", ""),
                authors=p.get("authors", []),
                year=p.get("year", 1900),
                pmid=p.get("pmid"),
                doi=p.get("doi"),
                abstract=p.get("abstract"),
                journal=p.get("journal"),
                keywords=p.get("keywords", []),
                paper_type=paper_type,
            )
        )
    return papers


class TokenCountingClient:
    """包装 LLMClient，追踪 token 消耗。

    DeepSeek 定价（2024-2025）：input ¥2/M, output ¥8/M。
    """

    def __init__(self, inner: LLMClient):
        self.inner = inner
        self.total_in = 0
        self.total_out = 0
        self.n_calls = 0
        self.n_failures = 0

    def complete_json(self, system: str, user: str) -> list[dict]:
        """代理 complete_json，记录 token usage。"""
        try:
            # litellm response 带 usage；通过底层 _call_once 拿不到 usage
            # 直接用 litellm.completion 走一次，保留 client 配置
            import litellm
            kwargs = {
                "model": self.inner._litellm_model_string(),
                "api_key": self.inner.api_key,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": self.inner.temperature,
                "max_tokens": self.inner.max_tokens,
            }
            if self.inner.base_url:
                kwargs["api_base"] = self.inner.base_url

            response = litellm.completion(**kwargs)
            content = response.choices[0].message.content

            # 记录 usage
            usage = getattr(response, "usage", None)
            if usage:
                self.total_in += getattr(usage, "prompt_tokens", 0) or 0
                self.total_out += getattr(usage, "completion_tokens", 0) or 0
            self.n_calls += 1

            # 复用 client 的 JSON 解析逻辑
            from src.llm_client import LLMClient as _LC
            # 手动 strip fence + parse（复用逻辑）
            stripped = self.inner._strip_code_fence(content)
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
            return []
        except Exception as e:
            self.n_failures += 1
            logger.warning(f"LLM call failed: {type(e).__name__}: {e}")
            return []

    def cost_cny(self) -> float:
        """估算人民币成本（DeepSeek-chat: in ¥2/M, out ¥8/M）。"""
        return self.total_in / 1_000_000 * 2 + self.total_out / 1_000_000 * 8


def extract_one(paper: Paper, primary_prompt: str, review_prompt: str | None,
                config: dict, client) -> list:
    """单篇 extraction（线程池 worker）。

    注意：LLMClient 本身是线程安全的（每次 litellm.completion 独立），
    但 TokenCountingClient 的计数器需要加锁。
    """
    import threading
    # 按类型路由 prompt
    if paper.paper_type == "review" and review_prompt:
        prompt = review_prompt
    else:
        prompt = primary_prompt

    try:
        ev = extract_evidence(paper, prompt, config, client)
        return (paper, ev, None)
    except Exception as e:
        return (paper, [], str(e))


def main():
    parser = argparse.ArgumentParser(description="无偏 corpus extraction")
    parser.add_argument("config", help="config YAML 路径")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 篇（smoke test）")
    parser.add_argument("--concurrent", type=int, default=None, help="并发数（覆盖 config）")
    parser.add_argument("--output-suffix", default="", help="输出文件后缀（如 _smoke20）")
    args = parser.parse_args()

    load_env(str(PROJECT_ROOT / ".env"))

    # 加载 config
    config = yaml.safe_load(open(args.config, encoding="utf-8"))
    search_cfg = config.get("search", {})
    json_path = search_cfg.get("papers_json")
    if not json_path or not Path(json_path).exists():
        print(f"ERROR: papers_json not found: {json_path}")
        sys.exit(1)

    # 并发数
    concurrent = args.concurrent or config.get("extraction", {}).get("concurrent", 1)

    # 加载论文
    papers = load_papers_from_json(json_path, limit=args.limit)
    n_review = sum(1 for p in papers if p.paper_type == "review")
    n_primary = len(papers) - n_review
    print(f"=== 无偏 corpus extraction ===")
    print(f"论文数: {len(papers)}（primary {n_primary}, review {n_review}）")
    print(f"并发: {concurrent}")

    # 加载 prompts
    extraction_cfg = config["extraction"]
    primary_prompt = load_prompt(extraction_cfg["prompt_file"])
    review_prompt_file = extraction_cfg.get("prompt_file_review")
    review_prompt = load_prompt(review_prompt_file) if review_prompt_file else None
    if review_prompt:
        print(f"Review-aware 双路径：启用（{n_review} review → 枚举, {n_primary} primary → 严格证据）")
    else:
        print(f"警告: 无 review prompt，全部走 primary 路径")

    # 创建带 token 计数的 client
    base_client = _make_llm_client(config)
    client = TokenCountingClient(base_client)

    # 跑 extraction
    print(f"\n=== 开始 extraction（{concurrent} 并发）===")
    t0 = time.time()
    all_evidence = []
    failures = []

    if concurrent <= 1:
        # 串行（smoke test 用）
        for i, paper in enumerate(papers, 1):
            result_paper, ev, err = extract_one(paper, primary_prompt, review_prompt, config, client)
            if err:
                failures.append((result_paper.id, err))
            all_evidence.extend(ev)
            if i % 5 == 0 or i == len(papers):
                elapsed = time.time() - t0
                print(f"  [{i}/{len(papers)}] evidence={len(all_evidence)} "
                      f"calls={client.n_calls} fails={client.n_failures} "
                      f"({elapsed:.1f}s, ¥{client.cost_cny():.3f})")
    else:
        # 并发
        with ThreadPoolExecutor(max_workers=concurrent) as pool:
            futures = {
                pool.submit(extract_one, p, primary_prompt, review_prompt, config, client): p
                for p in papers
            }
            done = 0
            for fut in as_completed(futures):
                result_paper, ev, err = fut.result()
                if err:
                    failures.append((result_paper.id, err))
                all_evidence.extend(ev)
                done += 1
                if done % 50 == 0 or done == len(papers):
                    elapsed = time.time() - t0
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (len(papers) - done) / rate if rate > 0 else 0
                    print(f"  [{done}/{len(papers)}] evidence={len(all_evidence)} "
                          f"calls={client.n_calls} fails={client.n_failures} "
                          f"({rate:.1f}篇/s, ETA {eta:.0f}s, ¥{client.cost_cny():.3f})")

    elapsed = time.time() - t0
    print(f"\n=== 完成 ===")
    print(f"总耗时: {elapsed:.1f}s ({elapsed/60:.1f} 分钟)")
    print(f"总 evidence: {len(all_evidence)}")
    print(f"LLM 调用: {client.n_calls}（失败 {client.n_failures}）")
    print(f"Token 消耗: input {client.total_in:,} + output {client.total_out:,}")
    print(f"预估成本: ¥{client.cost_cny():.2f}")

    # 候选统计
    from collections import Counter
    cand_counter = Counter(e.core_name for e in all_evidence)
    level_counter = Counter(e.evidence_level for e in all_evidence)
    print(f"\n候选数（去重 core_name）: {len(cand_counter)}")
    print(f"Top 15 候选: {cand_counter.most_common(15)}")
    print(f"证据等级分布: {dict(level_counter)}")

    # 保存
    out_dir = PROJECT_ROOT / "cases/locust_sih" / config["output"]["dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"evidence_db{args.output_suffix}.json"

    # 序列化 Evidence dataclass
    from dataclasses import asdict
    evidence_dicts = []
    for e in all_evidence:
        d = asdict(e)
        evidence_dicts.append(d)

    output_data = {
        "source": "unbiased_papers.json",
        "n_papers": len(papers),
        "n_primary": n_primary,
        "n_review": n_review,
        "n_evidence": len(all_evidence),
        "n_candidates_unique": len(cand_counter),
        "n_failures": len(failures),
        "elapsed_sec": elapsed,
        "token_input": client.total_in,
        "token_output": client.total_out,
        "cost_cny": client.cost_cny(),
        "top_candidates": cand_counter.most_common(30),
        "level_distribution": dict(level_counter),
        "failures": failures[:20],
        "evidence": evidence_dicts,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 已保存到 {out_file}")


if __name__ == "__main__":
    main()
