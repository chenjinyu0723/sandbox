# MinerU DOCX/PPTX → Markdown

从 [MinerU](https://github.com/opendatalab/MinerU) 抽取的 DOCX/PPTX 独立转换工具。

## 快速开始

```bash
pip install -r requirements.txt
python main.py document.docx          # → document.md + document_images/
python main.py presentation.pptx      # → presentation.md + presentation_images/
```

## 参数说明

```
python main.py <文件路径> [-o 输出路径] [--images-dir 图片目录] [--no-images]

  <文件路径>       .docx 或 .pptx 文件路径（必需）
  -o, --output     输出 .md 文件路径（默认：同目录、同名、.md 后缀）
  --images-dir     图片输出目录（默认：<文件>_images/）
  --no-images      不提取图片，仅输出文本（NLP_MD 模式）
```

## 示例

```bash
# 基本用法：转换后输出在文件同目录
python main.py C:\reports\季度总结.docx
# → C:\reports\季度总结.md
# → C:\reports\季度总结_images\  （所有图片）

# 指定输出路径
python main.py C:\reports\季度总结.docx -o C:\output\report.md

# 指定图片目录
python main.py C:\reports\季度总结.docx --images-dir img

# 纯文本模式（不提取图片）
python main.py C:\reports\季度总结.docx --no-images
```

## 支持的格式

| 来源 | 输出 |
|------|------|
| .docx | 标题 # ##、表格 `<table>`、图片 `![]()`、公式 `$...$`、列表、目录、超链接、字体样式 |
| .pptx | 标题、表格 `<table>`、图片 `![]()`、公式、列表、演讲者备注 |

## 目录结构

```
MinerU/
├── main.py                 ← 入口
├── requirements.txt
├── README.md
└── mineru/                 ← MinerU 抽取的源码
    ├── backend/office/     ← Office 后端（Block→Markdown 转换）
    ├── model/docx/         ← DOCX 解析器
    ├── model/pptx/         ← PPTX 解析器
    └── utils/              ← 工具函数
```
