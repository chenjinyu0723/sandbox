---
name: excel-processor
description: "Use when the user wants to clean, deduplicate, filter, or transform large Excel files (multi-sheet) with Polars. Supports per-sheet dedup (AND/OR logic), null-dropping, and statistical filtering (median/mean/mode/outlier thresholds)."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [excel, polars, xlsx, dedup, filter, data-cleaning]
    related_skills: [document-to-markdown]
---

# Excel 大文件处理 — Polars + Calamine

## Overview

处理超大型 Excel 文件（百万行级别），对每个子表独立执行**去重 / 去空 / 条件筛选**三个算子，输出到新的 Excel 文件。

核心脚本：`scripts/xlsx_processor.py`（一个自包含的 Python 文件，~1300 行，中文注释全覆盖）

底层引擎：Polars + Calamine（FastExcel），逐表处理，控制内存。

## When to Use

- 用户需要对 Excel 做批量清洗：去重、删除空行、按条件筛选
- Excel 有多个子表，每个子表的处理规则不同
- 数据量大（几十万行以上），担心内存爆炸
- 筛选条件需要用到统计量（中位数、均值、众数、异常值边界）

Don't use for:
- 简单的单表去重（直接用 Polars `.unique()` 更简单）
- 格式美化 / 合并单元格 / 图表（这不是数据清洗）
- 交互式 Excel 操作（用 computer-use 打开 Excel 手动操作）

## Quick Start

```bash
# 1. 确认依赖
pip install polars fastexcel xlsxwriter

# 2. 看懂配置结构（生成示例文件）
python scripts/xlsx_processor.py --generate-example config.example.json

# 3. 按需修改配置
#    编辑 config.example.json → 改成自己的 input_path 和 sheets 配置

# 4. 先 dry-run 验证配置
python scripts/xlsx_processor.py --config config.example.json --dry-run

# 5. 正式执行
python scripts/xlsx_processor.py --config config.example.json
```

## Configuration Structure

配置文件是 JSON 格式，三层结构：

```json
{
  "input_path": "C:/data/原始.xlsx",       // 必填：输入文件路径
  "output_path": null,                       // 可选：输出路径（null=自动生成）
  "output_suffix": "_processed",             // 输出后缀（默认 _processed）
  "sheets": {                                // 逐表配置
    "Sheet名称": {
      "operations": [
        // 算子列表，按顺序执行
        { "type": "filter",       "logic": "and/or", "conditions": [...] },
        { "type": "drop_nulls",   "columns": [...],  "logic": "or/and" },
        { "type": "deduplicate",  "columns": [...],  "logic": "and/or" }
      ]
    }
  },
  "global": {
    "skip_sheets": [],           // 跳过的子表
    "only_sheets": null,         // 仅处理的子表（null=全部）
    "engine": "calamine"         // 读取引擎
  }
}
```

### 三个算子详解

**1. filter — 条件筛选**

```json
{
  "type": "filter",
  "logic": "and",              // "and"(交): 全部满足 / "or"(并): 任一满足
  "conditions": [
    {
      "column": "金额",        // 要比较的列名
      "operator": ">=",        // >  <  >=  <=  ==  !=
      "value_type": "median",  // literal | median | mean | mode | outlier_lower | outlier_upper
      "value_column": "金额",  // 统计量来源列（默认=column）
      "value": null            // 仅 value_type="literal" 时填具体值
    }
  ]
}
```

`value_type` 速查：
| value_type       | 含义                              |
|-----------------|-----------------------------------|
| `literal`       | 直接使用 `value` 字段的值          |
| `median`        | 该列中位数                         |
| `mean`          | 该列均值                           |
| `mode`          | 该列众数（出现最多的值）            |
| `outlier_lower` | Q1 - 1.5×IQR（下异常值边界）        |
| `outlier_upper` | Q3 + 1.5×IQR（上异常值边界）        |

**2. drop_nulls — 删除含空值行**

```json
{
  "type": "drop_nulls",
  "columns": ["客户名", "金额"],
  "logic": "or"              // "or"(默认): 任一列为空即删 / "and": 全空才删
}
```

**3. deduplicate — 去重**

```json
{
  "type": "deduplicate",
  "columns": ["订单号", "客户名"],
  "logic": "and"             // "and"(交): 组合去重 / "or"(并): 独立去重
}
```

**交(AND) vs 并(OR) 去重语义：**

| logic | 语义 | 示例 |
|-------|------|------|
| `and` | 列值**组合**相同 → 重复 | ("张三","100") 与 ("张三","100") 重复 → 保留第一行 |
| `or`  | 任一列的值**独立**出现过 → 删除 | A="张三"在第1行见过 → 后续有"张三"的行全删；B=100在第2行见过 → 后续有100的行全删 |

## Workflow for the Agent

1. **理解需求**：用户会描述对哪些表、哪些列做什么操作（去重/去空/筛选）
2. **写 JSON 配置**：按上面结构写出配置文件，参考 `scripts/xlsx_processor.py` 头部注释
3. **dry-run 验证**：`python scripts/xlsx_processor.py --config <config> --dry-run`
4. **正式执行**：`python scripts/xlsx_processor.py --config <config>`
5. **报告结果**：脚本会输出详细的处理前后行数、保留率

If the user does NOT provide a config file path, generate one based on their description, then run it.

## Common Pitfalls

1. **列名不匹配**：Excel 表头与 config 中的 `column` 必须严格一致（含空格、大小写）。如果列名对不上，脚本会报 `KeyError` 并列出前 10 个可用列名。
2. **统计量计算失败**：如果整列都是 null 或非数值，`median/mean/outlier_*` 会报错。先用 `drop_nulls` 或换 `literal` 模式。
3. **"or" 去重太激进**：独立去重可能删掉大量行，建议先用 `--dry-run` 看配置是否合理，或先用小样试验。
4. **内存警告**：单表超过 500MB 时脚本会打印 WARNING。如果确实 OOM，建议先转 parquet 再处理。
5. **输出覆盖**：如果输出文件已存在，脚本会打印警告并直接覆盖。确认路径正确。

## Verification Checklist

- [ ] `pip install polars fastexcel xlsxwriter` 全部安装成功
- [ ] `--dry-run` 通过，无 ValidationError
- [ ] 输出文件生成在预期路径
- [ ] 输出子表数量、名称、顺序与原表一致（skip 的除外）
- [ ] 抽查 3-5 行验证去重/去空/筛选逻辑正确

## One-Shot Recipes

### 全表去重（组合列）
```json
{"type": "deduplicate", "columns": ["订单号", "日期"], "logic": "and"}
```

### 删除含空行
```json
{"type": "drop_nulls", "columns": ["姓名", "电话"], "logic": "or"}
```

### 筛选金额大于中位数的已完成订单
```json
{
  "type": "filter", "logic": "and",
  "conditions": [
    {"column": "金额", "operator": ">=", "value_type": "median"},
    {"column": "状态", "operator": "==", "value_type": "literal", "value": "已完成"}
  ]
}
```

### 筛选金额不在异常值范围内的行（剔除异常值）
```json
{
  "type": "filter", "logic": "and",
  "conditions": [
    {"column": "金额", "operator": ">=", "value_type": "outlier_lower"},
    {"column": "金额", "operator": "<=", "value_type": "outlier_upper"}
  ]
}
```
