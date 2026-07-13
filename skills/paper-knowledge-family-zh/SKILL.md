---
name: paper-knowledge-family-zh
description: "Orchestrate a Chinese paper knowledge workflow family: single-paper notes, topic archive sync, overview/academic/engineering surveys, and recurring topic maintenance."
---

# Paper Knowledge Family ZH

## Family Overview

This is the orchestration skill for the paper knowledge workflow family.

It coordinates four layers:

1. `evidence-grounded-paper-notes-zh`
2. `paper-topic-archive-zh`
3. `paper-topic-survey-zh`
4. `paper-topic-maintenance-zh`

## Core Principle

单篇论文不是终点。只要它属于某个已经形成的主题阅读线，就继续进入：

`单篇笔记 -> 专题归档 -> 综述刷新 -> 定期维护`

## Default Family Contract

After a same-type paper is processed:

1. the paper note must exist and be marked as read
2. the paper must be folded into the correct topic archive
3. the topic index and inventory must be refreshed
4. the topic overview, academic survey, and engineering survey must be refreshed when needed

## Reuse Pattern

This family pattern fits topic corpora such as:

- Text-to-SQL / NL2SQL
- computational social science
- memory systems
- any future literature program where new papers should accumulate into a living corpus

## Important Boundary

If the user asks only to install or solidify the family as skills, do that first.
If the user asks to run the family on a live corpus, the run is not complete until archive and survey phases have also been handled.
