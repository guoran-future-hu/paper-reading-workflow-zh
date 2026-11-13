---
name: paper-topic-survey-zh
description: "Build and maintain topic-level overview, academic, and engineering surveys from an archived same-type paper corpus."
---

# Paper Topic Survey ZH

## Purpose

把专题语料库转成长期可维护的综述资产。这个 skill 负责在 topic archive 完整之后，生成并持续更新三类文档：

1. `全景综述`：短一些的总览版
2. `学术综述`：按论文综述/学术报告写法展开
3. `工程综述`：按系统设计、模块落地、成本与风控视角展开

## Default Output Pattern

For topic folder `<ARCHIVE_ROOT>/<topic>/`, keep:

```text
<topic> 全景综述（N篇）.md
<topic> 学术综述（N篇）.md
<topic> 工程综述（N篇）.md
```

`N` must reflect the current archived paper-note count.

## Survey Contract

### 1. 全景综述

Use this as the topic landing page.

Must include:

- corpus scope
- year distribution
- one-sentence conclusion
- method map
- benchmark / evaluation summary
- major open problems
- links to academic and engineering long-form surveys

### 2. 学术综述

Write this like a real scholarly survey or internal review article.

Should include:

- 摘要
- 关键词
- 引言
- 范围与统计
- 任务定义与形式化
- 发展脉络
- 方法谱系
- benchmark 与评测问题
- 跨论文综合结论
- 开放问题
- 结论

Focus on:

- conceptual structure
- taxonomy
- research problem migration
- methodological comparison
- evaluation logic

### 3. 工程综述

Write this like a serious system design and deployment review.

Should include:

- 摘要
- 工程问题定义
- why single-model framing is insufficient
- layered architecture
- upstream cleaning / routing / metadata / retrieval
- context packing
- candidate generation
- repair / verification / risk control
- memory / continual adaptation
- observability / cost / latency
- practical rollout roadmap
- engineering conclusions

Focus on:

- what to build
- what to instrument
- where systems fail in production
- what trade-offs recur across papers

## Update Policy

This skill is not one-shot.

Whenever new same-topic papers are archived:

1. update corpus count
2. revise year distribution
3. insert newly important representative papers
4. update method map if a new subline appears
5. update open problems if the corpus shifts
6. keep survey links in the topic index current

Do not leave surveys frozen at an older count after the topic corpus has changed.

## Quality Bar

These surveys must be:

- detailed, not outline-only
- English-first
- academically toned even in the engineering version
- grounded in the actual archived notes, not generic background
- internally linked to representative papers in the archive

## Completion Criteria

Do not report survey work complete unless:

- all three survey files exist
- counts in file names and body match the current corpus size
- topic index links all survey files
- survey note links resolve in Obsidian
- surveys mention newly added same-topic papers when they materially shift the corpus

## Relationship To Other Skills

- Run `paper-topic-archive-zh` first.
- Pair with `paper-topic-maintenance-zh` for periodic refresh.
