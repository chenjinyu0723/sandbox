---
name: vlm-bbox-detection
description: >
  Use a VLM (Qwen-VL / GPT-4V / Claude) to iteratively detect and annotate
  objects with bounding boxes. The skill reads image dimensions, prompts the
  VLM for bbox coordinates, draws them with Chinese labels (same objects
  numbered: 扫描枪1, 扫描枪2, ...), saves to JSON, then feeds the annotated
  image back to the VLM for verification and iterative refinement until the
  VLM confirms the boxes are accurate.
triggers:
  - 标注/标框/框出/标出/检测/定位/识别/找一下/看看有没有/标记/画框/bbox/bounding box/画出来
metadata:
  hermes:
    tags: [vlm, detection, bbox, annotation, iterative-refinement]
    category: computer-use
    related_skills: []
---

# VLM 迭代标注 Skill

利用 VLM（如 Qwen-VL、GPT-4V）对图片中的指定物体进行检测和标注。
核心流程：**获取图片尺寸 → VLM 粗定位 → 画框 → 反馈验证 → 迭代调整 → 确认完成**。

## 使用方式

用户说"帮我标出图片里的扫描枪和护目镜"，Agent 自动执行全流程。

## 完整工作流

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 读图获取尺寸 (width, height)                         │
│   → 用 Python 脚本读取图片，拿到宽高信息                      │
├─────────────────────────────────────────────────────────────┤
│ Step 2: Prompt VLM 给出 bbox                                 │
│   → 告知图片尺寸，要求输出物体名称 + bbox 坐标                │
│   → 响应格式: {"objects": [{"name": "扫描枪", "bbox": [...]}]}│
├─────────────────────────────────────────────────────────────┤
│ Step 3: 解析 → 画框 → 存 JSON                                │
│   → 解析 VLM 返回的坐标                                     │
│   → 用指定颜色画框 + 中文标签（相同物体编号：扫描枪1、扫描枪2）│
│   → 保存 JSON 到工作目录                                     │
├─────────────────────────────────────────────────────────────┤
│ Step 4: 反馈标注图给 VLM 验证                                │
│   → 将画好框的图发给 VLM                                    │
│   → 询问：哪些框不准？应该往哪个方向调？调多少？              │
├─────────────────────────────────────────────────────────────┤
│ Step 5: 迭代调整                                             │
│   → 如果不准，VLM 给出每个框的调整方向和幅度                 │
│   → 调整坐标 → 重新画框 → 再次验证                          │
│   → 重复直到 VLM 确认"所有框都准确"                         │
└─────────────────────────────────────────────────────────────┘
```

## Agent 执行指南

### Step 1: 获取图片尺寸

```bash
python -c "from PIL import Image; img = Image.open('图片路径'); print(f'width={img.width}, height={img.height}')"
```

### Step 2: 构造 Prompt 发给 VLM

用 `execute_code` 或直接构造 prompt。关键要点：
- **必须告知图片的实际像素尺寸**
- 要求输出标准 JSON 格式
- bbox 格式统一为 `[x1, y1, x2, y2]`（左上角和右下角的像素坐标）

Prompt 模板（发送给 VLM）：

```
这张图片的尺寸是 {width} x {height} 像素。

请你在图片中找出所有的"扫描枪"和"护目镜"（barcode scanner, safety goggles），
并给出每个物体的精确 bounding box 坐标。

请以 JSON 格式返回：
{
  "objects": [
    {"name": "扫描枪", "bbox": [x1, y1, x2, y2]},
    {"name": "护目镜", "bbox": [x1, y1, x2, y2]}
  ]
}

注意：
1. 坐标是像素坐标，基于图片的实际尺寸 ({width} x {height})
2. x1,y1 是 bounding box 左上角坐标，x2,y2 是右下角坐标
3. 如果有多个相同物体，请在 name 中加上编号（如 "扫描枪1", "扫描枪2"）
4. 坐标必须在图片范围内 (x: 0~{width}, y: 0~{height})
5. 只输出 JSON，不要解释
```

### Step 3: 解析 + 画框 + 存 JSON

运行脚本 `references/draw_and_save.py`：

```bash
python references/draw_and_save.py \
  --image "原图路径" \
  --json '从VLM响应中提取的JSON字符串' \
  --output "标注后图片路径" \
  --json-output "结果JSON路径"
```

脚本功能：
- 解析 VLM 返回的 JSON
- 为不同类别分配不同颜色
- 相同物体自动编号（扫描枪1、扫描枪2...）
- 使用中文字体（Windows 自动查找可用中文字体）
- 保存 JSON 结果

### Step 4: 验证与迭代调整

将标注后的图片再次发给 VLM，验证 Prompt：

```
这张图片已经在上面画了 bounding box 标注框。

请你逐个检查每个标注框是否准确包围了目标物体：

1. 对每个框，请说明：
   - 框是否准确包围了目标物体？
   - 如果不够准确，应该往哪个方向调整（上/下/左/右/扩大/缩小）？大约调整多少像素？

2. 按以下格式回复（JSON）：
{
  "all_correct": false,
  "adjustments": [
    {
      "name": "扫描枪1",
      "current_bbox": [x1, y1, x2, y2],
      "accurate": false,
      "direction": "向左扩展",
      "pixels": 15,
      "new_bbox": [105, 200, 320, 380]
    }
  ]
}

如果所有框都准确，设置 "all_correct": true，"adjustments" 为空数组。
```

迭代终止条件：VLM 返回 `"all_correct": true` 或达到最大迭代次数（默认 5 轮）。

### Step 5: 记录过程

每轮迭代都要在回复中输出：
- 本轮 VLM 对每个物体的描述（物体在哪里）
- 当前 bbox 坐标
- 调整方向和幅度
- 是否完成

## JSON 输出格式

```json
{
  "image": {
    "path": "C:/path/to/image.jpg",
    "width": 1920,
    "height": 1080
  },
  "prompt_objects": ["扫描枪", "护目镜"],
  "iterations": 3,
  "objects": [
    {
      "name": "扫描枪1",
      "bbox": [120, 200, 320, 380],
      "color": "#FF4444",
      "iteration_history": [
        {"round": 1, "bbox": [100, 180, 340, 400], "vlm_feedback": "偏大，需缩小"},
        {"round": 2, "bbox": [115, 195, 325, 385], "vlm_feedback": "右边界需再收一点"},
        {"round": 3, "bbox": [120, 200, 320, 380], "vlm_feedback": "准确"}
      ]
    },
    {
      "name": "护目镜1",
      "bbox": [500, 150, 680, 280],
      "color": "#4444FF",
      "iteration_history": [...]
    }
  ]
}
```

## 颜色方案

默认颜色表（不同物体类别用不同颜色）：

| 物体类别 | 颜色 | 色值 |
|---------|------|------|
| 扫描枪 | 红色系 | #FF4444 |
| 护目镜 | 蓝色系 | #4488FF |
| 其他默认 | 绿色系 | #44BB44 |
| 冲突时自动轮转 | 橙色系 | #FF8844 |

相同类别、不同编号的物体用同一色系但微调色调区分。

## 中文字体处理

Windows 字体查找优先级：
1. `C:\Windows\Fonts\simhei.ttf` (黑体)
2. `C:\Windows\Fonts\msyh.ttc` (微软雅黑)
3. `C:\Windows\Fonts\simsun.ttc` (宋体)
4. 回退到 PIL 默认字体 + 拼音标注

## 约束与注意事项

- **Agent 不能直接调用 VLM** — Agent 需要通过 `execute_code` 中的文字 prompt 来模拟，或直接输出 prompt 让用户在 VLM 界面使用。实际操作中：Agent 构造好 prompt，用户发给 Qwen，Agent 读取响应后继续。
- 如果用户是在与 Agent 对话（Agent 本身是多模态的），Agent 可以直接看图给出 bbox，然后走画框→验证流程。
- 最大迭代次数默认 5 轮，避免死循环。
- 如果多轮后仍不准确，标记为 "需要人工复核"。
