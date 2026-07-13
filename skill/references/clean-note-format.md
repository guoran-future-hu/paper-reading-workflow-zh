# Clean Chinese Obsidian Note Format

Formal notes must be clean, Chinese-first, and useful for repeated reading. The backend evidence report can stay strict and mechanical; the formal note should not feel like a validator artifact.

## Frontmatter

Keep YAML frontmatter with at least:

```yaml
title: "<original paper title>"
authors: "<authors>"
year: <year>
arxiv: "<id if any>"
reading_date: YYYY-MM-DD
status: 已读
read_marker: 已读
source_pdf: "pdfs/<file>.pdf"
tags:
  - 论文阅读
```

## Required Structure

Use exactly these 14 second-level sections:

```md
# <original paper title>

## PDF 原文

![[pdfs/<file>.pdf]]

## 已读信息

## 1. 一句话总览

## 2. 论文基本信息

## 3. 研究问题

## 4. 核心方法

## 5. 关键图表解读

## 6. 实验与结果

## 7. 公式与技术细节

## 8. 核心概念解释

## 9. 创新点与深度理解

## 10. 局限与批判

## 11. 和已读论文的关系

## 12. 对我的启发
```

## Style Rules

- H1 keeps the original paper title.
- Body prose is Chinese-first.
- Keep English only for:
  - original paper title
  - author names
  - model/method names where translation would be awkward
  - formulas and symbols
  - file paths
  - necessary original quoted terms
- Avoid raw backend terms in the formal note:
  - `Evidence`
  - `Inference`
  - `Not clearly stated in the paper`
  - `MinerU`
  - `full_text`
  - `paper_index`
  - `evidence_cards`
  - `完整性自检`
  - `作者做了什么`
  - `作者如何验证`
- Avoid duplicate structures. Do not include both old expert-note headings and strict backend report headings.

## Figure Section

`## 5. 关键图表解读` must embed every item in `figure_manifest.json`.

Use this style:

```md
### 图表 1：图 1

![图表 1：图 1](_evidence_reports/<paper-slug>/extracted/figures/001-figure-1.png)

原文锚点：`Figure 1: The Transformer - model architecture.`

图表定位：这张图展示 Transformer 的编码器-解码器架构。重点不是泛泛说“系统结构”，而是看输入嵌入、位置编码、自注意力、前馈网络、残差连接和层归一化如何串起来。

读法：沿数据流从输入端读到输出端，把每个模块对应到正文的方法定义；表格则先看行列定义、指标单位、基线和最优值；曲线图先看横轴、纵轴、图例和置信区间。

可以支持的结论：它能说明论文怎样组织机制、指标或案例，并支撑该图表实际展示的局部论点。

不能推出：单张图表不能替代实验整体，也不能推出没有在图中呈现的模型、任务或部署条件。

来源：第 3 页，原文编号：图 1。
```

Do not place full English captions in the heading. Keep only a short original anchor when it prevents misreading; the explanation itself must be Chinese-first.

Each visual block must:

- Ground the explanation in the original caption and nearby text, not in a generic phrase such as “这张图展示方法或系统结构”.
- State what the visual actually displays: architecture, workflow, complexity table, ablation table, benchmark result, dataset composition, embedding distribution, prompt template, case trajectory, or configuration table.
- Explain how to read it: axes and legends for charts, rows/columns/metrics for tables, data or control flow for architecture diagrams, input/action/output for cases.
- State what conclusion it can support and what it cannot support.
- Preserve page and original figure/table number.

## Formula Section

`## 7. 公式与技术细节` should include:

- formal definitions
- objectives/losses/reward functions
- probability updates or inference rules
- complexity terms
- evaluation metrics
- symbols and intuitive meanings

Use Obsidian/MathJax-safe syntax:

- Display formulas must use standalone `$$` delimiters:

```md
$$
R = w_{\mathrm{acc}} R_{\mathrm{acc}} + w_{\mathrm{len}} R_{\mathrm{len}}
$$
```

- Never use standalone single-dollar lines for display formulas.
- Prefer `\mathrm{...}` for textual subscripts such as `acc`, `len`, `exec`, `cand`, and `sim`.
- Before completion, scan formal notes for `^\$$`; any match in the frontend note is a rendering bug and must be fixed.

If the paper has few formulas, formalize the system as variables, inputs, outputs, and decision rules.

## Concept Section

`## 8. 核心概念解释` should explain why each concept matters and how it differs from neighboring concepts. Do not only list definitions.

## Deep Reading Sections

`## 9` to `## 12` should include:

- innovation claims
- mechanism-level understanding
- experiment and ablation interpretation
- failure modes
- relationship to already-read papers
- reusable design principles
- personal research or engineering implications
- follow-up questions
