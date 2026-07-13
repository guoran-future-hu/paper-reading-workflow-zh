---
name: paper-topic-maintenance-zh
description: "Maintain a living topic corpus: rescan for direct-topic notes, sync the archive, and incrementally refresh surveys after new same-type papers are written."
---

# Paper Topic Maintenance ZH

## Purpose

把专题论文库当成“活的知识库”维护，而不是一次性项目。这个 skill 固化三个长期动作：

1. 新论文写完后，检查它是否属于某个现有 topic
2. 定期扫描源目录，找出还没进专题归档的直接相关论文
3. 专题语料发生变化后，增量更新综述，而不是等用户反复提醒

## Maintenance Rule

After any newly processed paper note, ask internally:

1. 这篇是不是某个现有 topic 的直接同主题论文？
2. 如果是，该 topic archive 是否已经同步收录？
3. 如果 archive 增量变化了，综述是否已经刷新到新计数？

If the answer to any of these is no, the maintenance pass is not finished.

## Scan Discipline

Periodic scan means:

- scan source note root for same-type direct-topic notes
- compare against the topic archive note stems
- exclude adjacent but non-core papers
- resync archive if needed
- refresh surveys if the corpus size or composition changed

This does not require a fixed wall-clock schedule. It is a workflow obligation after new-paper processing or whenever the user asks for a corpus health check.

## Trigger Conditions

Run this skill when:

- a new paper in an existing topic was just processed
- the user asks “还有没有新的相关论文”
- the user asks whether an archive is complete
- a topic corpus already exists and the user wants it kept current

## Topic Health Checklist

For each active topic:

- archive note count is current
- no directly related source note remains unarchived
- index count matches paper count
- inventory count matches paper count
- overview / academic / engineering surveys all use the latest count
- survey link graph is intact

## Family Rule

Treat topic knowledge work as a skill family, not a single skill:

1. `evidence-grounded-paper-notes-zh` handles single-paper deep-read notes
2. `paper-topic-archive-zh` handles topic corpus sync
3. `paper-topic-survey-zh` handles overview + academic + engineering surveys
4. `paper-topic-maintenance-zh` keeps the corpus alive over time

## Forward Compatibility

The same family pattern should be reused for:

- computational social science topic corpora
- memory topic corpora
- any future repository-backed literature program the user provides

When a new topic repository or corpus is provided, start from:

1. source discovery
2. same-type clustering
3. archive sync
4. overview + academic + engineering survey generation

## Completion Criteria

Maintenance is complete only when:

- the latest same-type papers are in the topic archive
- survey counts and content are refreshed
- no directly related paper remains outside the archive

If the user only wants the skill family installed and not the maintenance pass run immediately, document the behavior in the skills and stop there.
