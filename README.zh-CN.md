<div align="center">

[![English](https://img.shields.io/badge/Language-English-555555?style=for-the-badge)](README.md) &nbsp; [![中文](https://img.shields.io/badge/语言-中文-2ea44f?style=for-the-badge)](README.zh-CN.md)

# Paper Reading Workflow ZH

### 面向 PDF、MinerU 与 Obsidian 的中文证据驱动读论文流程

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Local%20First-black?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Language-Python-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Notes-Obsidian-purple?style=for-the-badge" />
  <a href="https://github.com/LeoLin990405/paper-reading-workflow-zh/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/LeoLin990405/paper-reading-workflow-zh/ci.yml?branch=main&style=for-the-badge&label=CI" /></a>
  <img src="https://img.shields.io/badge/License-MIT-yellowgreen?style=for-the-badge" />
</p>

</div>

> 这是我本地读论文流程的可复用版本：下载 PDF，用 MinerU 抽取，保留严格证据层，再写成干净、可复读的中文 Obsidian 正式笔记。

---

## 概览

这个仓库把一套证据驱动的中文读论文流程整理成可复用 Skill 和辅助脚本。核心是双层结构：

1. 后端证据层：MinerU 抽取、图表清单、裁图、证据卡、严格报告
2. 前端笔记层：Obsidian 中干净可读的 14 节中文论文笔记

公开版已经做过脱敏：本机路径、私有 vault 名称、内网服务地址都替换成环境变量和示例配置。

## 1. 功能

- 通过 arXiv ID、URL 或标题解析并下载论文
- 调用本地 MinerU API 批量抽取 PDF
- 从 MinerU 输出生成图、表、chart 的证据清单
- 校验中文 Obsidian 正式笔记是否满足固定 14 节结构
- 记录已读标记和阅读索引
- 把临时阅读 inbox 和长期 topic archive 分开维护

## 2. 仓库结构

```text
.
├── skill/
│   ├── SKILL.md
│   └── references/
├── scripts/
│   ├── download_paper_opencli.py
│   ├── mineru_local_batch_extract.py
│   ├── build_figure_manifest.py
│   └── validate_clean_notes.py
├── paper_notes/
│   └── config.py
├── examples/
│   ├── paper-notes.config.example.json
│   └── read-marker.example.md
├── NOTICE.md
└── README.md
```

## 3. 依赖

- Python 3.10+
- `curl`
- `opencli`，用于论文解析，推荐安装
- 本地 MinerU API，用于 PDF 抽取
- 只有在裁图时才需要 Poppler `pdftoppm` 和 `Pillow`：

```bash
python -m pip install ".[visual]"
```

## 4. 快速开始

复制并编辑示例配置：

```bash
cp examples/paper-notes.config.example.json paper-notes.config.json
```

下载论文：

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

## 5. 流程契约

`skill/SKILL.md` 定义了完整工作契约：

- 源 PDF 进入配置好的 inbox
- 抽取证据放在 `_evidence_reports/<paper-slug>/`
- 最终 PDF 和正式笔记进入 topic archive
- 正式笔记必须使用 14 个二级标题
- 后端抽取痕迹不能污染前端正式笔记
- 图、表、chart 应进入 `figure_manifest.json`

完整规范见 `skill/references/workflow.md` 和 `skill/references/clean-note-format.md`。

## 6. 配置

可以使用 `paper-notes.config.json`，也可以设置环境变量：

```bash
export PAPER_NOTES_PDF_INBOX="$HOME/Papers/inbox"
export PAPER_NOTES_READING_INBOX="$HOME/Documents/Obsidian/ResearchVault/论文阅读"
export PAPER_NOTES_ARCHIVE_ROOT="$HOME/Documents/Obsidian/ResearchVault/论文笔记"
export PAPER_NOTES_STAGING_ROOT="$HOME/Archives/paper-reading-workflow"
export MINERU_LOCAL_URL="http://127.0.0.1:8010"
```

`paper-notes.config.json` 已加入 `.gitignore`，真实本地路径不会进仓库。

## 7. 致谢与来源说明

这个项目明确注明：它不是从零凭空发明的流程，而是在参考 [MoonKirito/evidence-grounded-paper-deep-read](https://github.com/MoonKirito/evidence-grounded-paper-deep-read) 这个 MIT License 的 paper-reading Skill 之后，结合我自己的本地实践继续迭代出来的版本。

我主要把它扩展到中文 Obsidian 笔记、MinerU 抽取、证据工作区、图表证据清单、已读标记和 topic archive 维护。

也感谢 [OpenCLI](https://github.com/jackwener/OpenCLI) 提供 adapter 式的论文发现能力，以及 [MinerU](https://github.com/opendatalab/MinerU) 提供文档到 Markdown/JSON 的抽取能力。没有这两个项目，这套流程会笨重很多。

公开仓库已经做过泛化和脱敏；私有路径和本地服务地址不会进入版本控制。更完整的来源说明见 `NOTICE.md`。

## 8. License

MIT。见 `LICENSE`。
