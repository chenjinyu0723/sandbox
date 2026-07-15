# 配套工具脚本使用说明

## 1. chm_to_folders.py —— 核心转换脚本

### 功能
1. 解析 .hhc 目录树文件（GB2312 编码）
2. 提取 HTML 文件的纯文本内容
3. 按层级创建文件夹结构，输出 .txt 文件

### 关键设计决策

**问题1：自闭合标签导致 skip_depth 累加**
- 现象：`<meta>` 等自闭合标签在 Python HTMLParser 中只触发 handle_starttag 不触发 handle_endtag，导致 skip_tags 计数只增不减，后续所有文本被跳过
- 解决：在 handle_starttag 中检测自闭合标签，立即回退 skip_depth

**问题2：Windows MAX_PATH 限制（260字符）**
- 现象：嵌套多层文件夹后路径超过限制，`os.makedirs()` 报错 FileNotFoundError
- 解决：使用 `\\?\` 前缀（Windows 扩展路径语法）+ 文件名截断到 40 字符

**问题3：.hhc 中 `<UL>` 和 `<OBJECT>` 同级混合**
- 现象：`<LI><OBJECT>...</OBJECT><UL>` 中 `<UL>` 在 OBJECT 之后，下一行的 OBJECT 应该更深
- 解决：用 `re.finditer` 扫描所有 `<UL>`/`</UL>` 的位置，对每个 OBJECT 统计它之前的 UL 嵌套数作为深度

### 运行

```bash
python chm_to_folders.py
```

前提：已在 `chm_extracted/` 目录下用 7-Zip 解包了 CHM 文件。

---

## 2. README 生成流程

### 第一步：提取所有命令的功能描述

用 `execute_code` 运行 Python，遍历所有 177 个文件夹，读取每条命令的"命令功能"段：

```python
def get_func_lines(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    in_func = False
    func_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == '命令功能':
            in_func = True
            continue
        if in_func:
            if stripped in ('命令格式', '参数说明', ...):
                break
            if stripped:
                func_lines.append(stripped)
    return ' '.join(func_lines)
```

### 第二步：按关键词生成类别描述

根据文件夹名称中的关键词（ACL、BGP、VRRP、WLAN 等）匹配预定义的类别描述模板，确保描述准确。

### 第三步：写入 README.md

每个文件夹的 README 结构：
```markdown
# 文件夹名

类别描述（1-2句话）

本目录包含 N 条命令：

- **命令名** - 功能简述（从命令功能段提取，截取前150字）
```

### 第四步：人工编写中层和顶层 README

章节级 README（20个）和顶层 README（2个）由人工根据子 README 内容总结编写，包含：
- 该章节覆盖的功能域概述
- 子目录导航表（名称 + 用途 + 适用场景）
- 常用命令快速查找清单
