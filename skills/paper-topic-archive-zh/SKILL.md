---
name: paper-topic-archive-zh
description: "Archive same-type paper notes into a dedicated topic folder, normalize note structure/frontmatter, and maintain a topic index and inventory."
---

# Paper Topic Archive ZH

## Purpose

把“单篇论文笔记”升级成“专题语料库”。当同类型论文已经形成一个连续阅读序列时，本 skill 负责：

1. 识别哪些笔记属于同一 topic。
2. 将这些笔记统一归档到 `<ARCHIVE_ROOT>/<topic>/`。
3. 统一 frontmatter、已读标记字段和 14 段正文结构。
4. 复制并校验配套 PDF 与 `_evidence_reports` 资源。
5. 维护专题索引和专题 inventory。

## Configuration

Use the same configuration contract as the main paper-note workflow:

- `PAPER_NOTES_READING_INBOX`
- `PAPER_NOTES_ARCHIVE_ROOT`
- `PAPER_NOTES_STAGING_ROOT`

The clean-note standard is defined in `skills/evidence-grounded-paper-notes-zh/references/clean-note-format.md`.

## When To Use

Use this skill when any of these is true:

- 用户说“把这些同类型论文单独归档”
- 用户说“统一格式”“归到一个子文件夹”
- 同一 topic 的论文数量已经足够形成专题语料
- 刚处理完一批新论文，需要把它们合并进已有 topic archive

## Topic Membership Rules

只归档“直接同主题”论文，不把边缘提及的论文硬塞进去。

优先依据：

1. frontmatter tags
2. 标题关键词
3. 一句话总览与研究问题
4. 是否与现有专题的核心任务、benchmark、方法线直接一致

需要保守归类，宁可少收一篇，也不要污染专题边界。

## Required Archive Outputs

For each topic folder, keep:

```text
<ARCHIVE_ROOT>/<topic>/
  *.md
  pdfs/*.pdf
  _evidence_reports/<slug>/
  <topic> 论文笔记归档索引.md
  _topic_inventory.json
```

## Normalization Rules

Every archived paper note must satisfy:

- same 14 H2 sections as the clean-note standard
- frontmatter includes at least:
  - `title`
  - `authors`
  - `year`
  - `reading_date`
  - `status: 已读`
  - `read_marker: 已读`
  - `source_pdf`
- PDF embed resolves
- figure embeds resolve
- note remains Chinese-first in body prose

If a note already has strong body content but heading names differ, restructure instead of rewriting from scratch.

## Index Rules

`<topic> 论文笔记归档索引.md` must include:

- total paper note count
- links to topic surveys when they exist
- archive path
- ordered note list

## Inventory Rules

`_topic_inventory.json` must track:

- topic name
- paper count
- source root
- destination root
- every note and its PDF
- every linked evidence report slug
- a `missing` array

Completion requires `missing = []`.

## Completion Criteria

Do not call the archive complete unless:

- no directly related paper note remains outside the topic archive
- every archived note matches the clean structure
- every archived note has the required frontmatter fields
- PDFs and evidence assets exist locally
- topic index exists
- topic inventory exists and `missing = []`

## Relationship To Other Skills

- Use `evidence-grounded-paper-notes-zh` for single-paper processing.
- Use `paper-topic-survey-zh` after archive sync to build or refresh surveys.
- Use `paper-topic-maintenance-zh` for recurring scan/sync discipline.
