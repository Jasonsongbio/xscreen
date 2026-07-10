# START HERE — 新 Claude 会话启动文档

> 这个文档是为了让你（新 Claude 会话）快速理解这个项目。请先读完本文档，再开始任务。

## 项目一句话总结

**xscreen** 是一个 AI 辅助的跨物种候选神经肽优先级筛选工具。从模式生物（果蝇等）文献中系统提取证据，通过同源映射到非模式生物（飞蝗等），输出可追溯的候选排名表，作为实验验证候选选择的依据。

## 项目的来源

这个工具为某个具体的生物学论文服务。

- 论文主题：NPF1a 介导飞蝗中阶段特异性的饥饿诱导运动过度（SIH）
- 论文位置：`/home/ug1708/workspace/Brain/ms_writing/npf/manuscript/manuscript_r1.md`
- 论文催生工具的根本问题：候选神经肽（AT, DH, sNPF, NPF1a）的选择标准论文里没说清，审稿人会质疑

## 工具的核心创新点（"占生态位"的关键）

1. **跨物种知识迁移**：从果蝇文献自动映射到目标物种（飞蝗等非模式生物）
2. **证据分层整合**：区分 transcript / peptide / release / functional 四个证据层级，加权评分
3. **可复用性**：其他研究者替换主题和物种即可复用，不为单一论文定制

## 当前状态（2026-07-08）

### 已完成
- 项目架构设计
- 配置模板（config/template.yaml）
- 模块骨架（src/ 下 6 个模块，接口已定义，实现为 stub）
- 本文案例（cases/locust_sih/）的配置

### 未完成（下一步任务）
- 接入真实 PubMed API（src/search.py 当前是 stub）
- 接入 Claude API 做证据提取（src/extract.py 当前是 stub）
- 接入 UniProt BLAST 做同源映射（src/homolog.py 当前是 stub）
- 实现评分逻辑（src/score.py 当前是 stub）
- 实现报告生成（src/report.py 当前是 stub）
- 端到端跑通 locust_sih 案例
- 人工核对 top 候选结果

## 关键约束

1. **短平快**：用户在赶投稿，工具要在 1-2 周内跑出真实结果
2. **可复用**：工具不是为本文定制，要能被其他研究者复用
3. **可追溯**：每个候选的每个判断都要附原始文献，可审计
4. **科学严谨**：不要"以终为始"预设结论，先跑出真实数据再写论文文字

## 与主论文项目的协作规则

- 主论文位置：`/home/ug1708/workspace/Brain/ms_writing/npf/`
- 主论文 Claude 会话已经讨论到第十七轮
- 主论文修改中，**与 AI 综述相关的部分暂停落地**（P53-P55, Abstract 第三句, Intro P24, Discussion P72 开头），等工具跑出真实结果再写
- 工具跑出的候选排名、证据表，将成为主论文的 Supplementary Table SX

## 第一步任务

1. 读 [CONTEXT.md](CONTEXT.md) 了解主论文的完整科学背景
2. 读 [README.md](README.md) 了解工具架构
3. 读 [config/template.yaml](config/template.yaml) 了解配置结构
4. 读 src/*.py 了解模块接口
5. 和用户确认下一步任务（见下节）

## 建议的下一步（等用户选）

- 选项 A：完善 search.py，接真实 PubMed API，先跑通文献检索
- 选项 B：完善 extract.py + prompt，先用少量文献（10-20 篇）测试 LLM 提取效果
- 选项 C：整体跑通 stub 流程（用 mock 数据），验证端到端架构
- 选项 D：用户自己有其他优先级

## 用户偏好（来自主论文讨论的积累）

- 不用破折号（em dash / en dash）
- 少用冒号
- 减少强调副词（itself, actually, indeed 等）
- 追求自然流畅，避免 AI 写作模式
- 科学严谨，避免过度声称
- 先充分讨论，后落地修改
