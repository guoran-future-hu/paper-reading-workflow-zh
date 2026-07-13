<div align="center">

[![English](https://img.shields.io/badge/Language-English-555555?style=for-the-badge)](README.md) &nbsp; [![中文](https://img.shields.io/badge/语言-中文-2ea44f?style=for-the-badge)](README.zh-CN.md)

# Paper Reading Workflow ZH

### 面向中文论文笔记、专题归档和综述的本地优先证据工作流

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Local%20First-black?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Language-Python-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Workflow-Skills%20%2B%20Obsidian-purple?style=for-the-badge" />
  <a href="https://github.com/LeoLin990405/paper-reading-workflow-zh/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/LeoLin990405/paper-reading-workflow-zh/ci.yml?branch=main&style=for-the-badge&label=CI" /></a>
  <img src="https://img.shields.io/badge/License-MIT-yellowgreen?style=for-the-badge" />
</p>

</div>

> 把零散 PDF 变成一个活的中文研究语料库：源文件、抽取证据、Obsidian 笔记、专题归档、全景/学术/工程综述彼此连起来。

---

## 概览

Paper Reading Workflow ZH 把一套本地读论文实践整理成可复用的 Codex Skills 和 Python 辅助脚本。它面向的不是一次性摘要，而是可追溯、可复读、可继续生长的论文知识库。

工作流分成两个层级：

- **单篇论文：** 下载或登记 PDF，抽取文本和图表，保留证据制品，写成 14 节中文 Obsidian 笔记，并创建已读标记。
- **专题语料：** 把同类型论文并入 topic archive，维护 inventory，并刷新全景综述、学术综述和工程综述。

公开仓库不会保存私有路径和本地服务地址。真实位置通过环境变量或 `paper-notes.config.json` 配置，后者已加入 `.gitignore`。

## 1. 处理对象

| 层级 | 产物 | 作用 |
|---|---|---|
| 论文 inbox | PDF 与已读标记 | 明确源文件和阅读状态 |
| 证据工作区 | MinerU JSON/Markdown、图表、manifest、报告 | 保留抽取和论点证据 |
| 正式笔记 | 14 节中文 Obsidian 笔记 | 让论文可读、可复查 |
| 专题归档 | 笔记、PDF、`_evidence_reports`、索引、inventory | 把同类型论文变成语料库 |
| 专题综述 | `全景综述`、`学术综述`、`工程综述` | 把语料库转成可复用综合判断 |

## 2. 工作流地图

```text
论文标题 / URL / PDF
  -> OpenCLI 辅助发现
  -> PDF inbox
  -> MinerU 抽取
  -> 证据工作区
  -> 图表证据清单
  -> 中文 Obsidian 正式笔记
  -> 已读标记 + 阅读索引
  -> 专题归档
  -> 全景 / 学术 / 工程综述
  -> 持续维护
```

主 Skill 在 `skill/SKILL.md`。topic-family Skills 在 `skills/`。

## 3. 仓库结构

```text
.
├── skill/
│   ├── SKILL.md
│   └── references/
├── skills/
│   ├── paper-knowledge-family-zh/
│   ├── paper-topic-archive-zh/
│   ├── paper-topic-survey-zh/
│   └── paper-topic-maintenance-zh/
├── scripts/
│   ├── download_paper_opencli.py
│   ├── mineru_local_batch_extract.py
│   ├── build_figure_manifest.py
│   └── validate_clean_notes.py
├── paper_notes/
│   └── config.py
├── examples/
├── NOTICE.md
└── README.md
```

## 4. 依赖

- Python 3.10+
- `curl`
- [OpenCLI](https://github.com/jackwener/OpenCLI)，用于论文发现，推荐安装
- 本地 [MinerU](https://github.com/opendatalab/MinerU) API，用于 PDF 抽取
- 只有裁图时才需要 Poppler `pdftoppm` 和 `Pillow`：

```bash
python -m pip install ".[visual]"
```

## 5. 快速开始

克隆并本地安装：

```bash
git clone https://github.com/LeoLin990405/paper-reading-workflow-zh.git
cd paper-reading-workflow-zh
python -m pip install -e .
```

创建私有配置：

```bash
cp examples/paper-notes.config.example.json paper-notes.config.json
```

下载或登记论文：

```bash
python scripts/download_paper_opencli.py \
  --query "Attention Is All You Need" \
  --config paper-notes.config.json
```

用 MinerU 抽取 PDF：

```bash
python scripts/mineru_local_batch_extract.py --config paper-notes.config.json
```

生成图表证据清单：

```bash
python scripts/build_figure_manifest.py --config paper-notes.config.json
```

校验正式笔记：

```bash
python scripts/validate_clean_notes.py --config paper-notes.config.json
```

## 6. 配置

可以使用 `paper-notes.config.json`，也可以设置环境变量：

```bash
export PAPER_NOTES_PDF_INBOX="$HOME/Papers/inbox"
export PAPER_NOTES_READING_INBOX="$HOME/Documents/Obsidian/ResearchVault/论文阅读"
export PAPER_NOTES_ARCHIVE_ROOT="$HOME/Documents/Obsidian/ResearchVault/论文笔记"
export PAPER_NOTES_STAGING_ROOT="$HOME/Archives/paper-reading-workflow"
export MINERU_LOCAL_URL="http://127.0.0.1:8010"
```

`examples/paper-notes.config.example.json` 记录了同一组字段。真实配置留在本地即可。

## 7. Skill Family

| Skill | 作用 |
|---|---|
| `evidence-grounded-paper-notes-zh` | 单篇论文下载、抽取、写笔记、已读标记 |
| `paper-knowledge-family-zh` | 编排整套论文知识流 |
| `paper-topic-archive-zh` | 把同类型论文收进专题归档 |
| `paper-topic-survey-zh` | 维护 `全景综述`、`学术综述` 和 `工程综述` |
| `paper-topic-maintenance-zh` | 新论文加入后保持专题语料持续更新 |

核心规则是：

```text
单篇笔记 -> 专题归档 -> 综述刷新 -> 持续维护
```

## 8. 笔记契约

正式 Obsidian 笔记使用固定 14 节结构：

```text
PDF 原文
已读信息
1. 一句话总览
2. 论文基本信息
3. 研究问题
4. 核心方法
5. 关键图表解读
6. 实验与结果
7. 公式与技术细节
8. 核心概念解释
9. 创新点与深度理解
10. 局限与批判
11. 和已读论文的关系
12. 对我的启发
```

`Evidence`、`Inference`、`MinerU`、`full_text`、`paper_index`、`evidence_cards` 等后端术语不应出现在 polished note 正文中。

## 9. 致谢

这个项目是在参考 [MoonKirito/evidence-grounded-paper-deep-read](https://github.com/MoonKirito/evidence-grounded-paper-deep-read) 之后继续迭代出来的；该项目是 MIT License 的 paper-reading Skill。

也感谢 [OpenCLI](https://github.com/jackwener/OpenCLI) 提供 adapter 式论文发现能力，以及 [MinerU](https://github.com/opendatalab/MinerU) 提供文档到 Markdown/JSON 的抽取能力。

更完整的来源说明见 `NOTICE.md`。

## 10. License

MIT。见 `LICENSE`。
