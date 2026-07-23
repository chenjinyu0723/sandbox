---
name: vlm-bbox-detection
description: >
  Let the agent (its own vision model) iteratively detect and annotate objects
  with bounding boxes. The agent reads image dimensions, directly gives bbox
  coordinates, draws them with Chinese labels (same objects numbered: 扫描枪1,
  扫描枪2, ...), saves to a fixed-name JSON ({prefix}_bbox.json). Then the agent
  reads the annotated image back, checks accuracy, adjusts coordinates in-place,
  and repeats until all boxes are confirmed accurate.
triggers:
  - 标注/标框/框出/标出/检测/定位/识别/找一下/看看有没有/标记/画框/bbox/bounding box/画出来
metadata:
  hermes:
    tags: [vlm, detection, bbox, annotation, iterative-refinement]
    category: computer-use
    related_skills: []
---

# Agent 视觉迭代标注

**你自己就是 VLM。** 直接看图给出 bbox，不需要构造 Prompt 发给外部模型。

核心流程：**获取图片尺寸 → 你直接给 bbox → 画框 → 你看图验证 → 迭代调整 → 确认完成**。

## 执行规则（Agent 必须遵守）

### 一、JSON 命名规则

JSON 文件名 = 原图文件名前缀 + `_bbox.json`，**全程不变**。

```
test.jpg        → test_bbox.json
工厂扫描枪.png   → 工厂扫描枪_bbox.json
```

### 二、每轮迭代你都必须说清楚

对每个目标物体，逐条说出：

```
扫描枪1：位于图片左下角工作台上，当前 bbox [120, 200, 320, 380]
  → 右边界偏左，没包住枪头 → 向右扩展 20px → 新 bbox [120, 200, 340, 380]

护目镜1：位于右上角桌面，当前 bbox [510, 160, 690, 290]
  → 框准确，不动
```

调整完成后一句话总结：**"本轮调整了 X 个框，仍需继续 / ✅ 全部准确"**。

### 三、迭代终止条件

- 你确认所有框都准确 → 终止
- 连续 2 轮无需调整 → 终止
- 最多 5 轮 → 终止并标记"需人工复核"

---

## 完整执行步骤

### Step 1: 获取图片尺寸

```bash
python -c "from PIL import Image; img = Image.open('图片路径'); print(f'width={img.width}, height={img.height}')"
```

### Step 2: 你直接看图给 bbox

你是多模态模型，直接看原图，输出 JSON。格式：

```json
{
  "image": {"width": 1920, "height": 1080},
  "objects": [
    {"name": "扫描枪1", "bbox": [120, 200, 320, 380]},
    {"name": "护目镜1", "bbox": [500, 150, 680, 280]}
  ]
}
```

规则：
- name 自带编号：扫描枪1、扫描枪2...
- bbox 用 `[x1, y1, x2, y2]` 像素坐标
- 找不到的物体不写

把 JSON 写入 `{prefix}_bbox.json`。

### Step 3: 画框

```bash
python references/draw_and_save.py \
  --image "原图" \
  --json "{prefix}_bbox.json" \
  --output "{prefix}_annotated.jpg" \
  --json-output "{prefix}_bbox.json"
```

### Step 4: 你读标注图，验证

重新看 `{prefix}_annotated.jpg`，逐个检查每个框。

说出判断后，**直接更新 `{prefix}_bbox.json`** 里的坐标。

然后用调整后的 JSON 重新画框：

```bash
python references/draw_and_save.py \
  --image "原图" \
  --json "{prefix}_bbox.json" \
  --output "{prefix}_annotated.jpg" \
  --json-output "{prefix}_bbox.json"
```

### Step 5: 重复 Step 4 直到确认全部准确

每轮标注图会覆盖上一轮，你只需要看最新那张。

---

## draw_and_save.py 说明

| 参数 | 说明 |
|------|------|
| `--image` | 原始图片路径（画框底图，不变） |
| `--json` | bbox 的 JSON 文件路径 |
| `--output` | 标注图输出路径 |
| `--json-output` | 更新后的 JSON 输出路径（通常和 --json 同一个文件） |

### 画框特性

- 不同类别不同颜色（扫描枪=红、护目镜=蓝...）
- 相同物体编号自动显示
- 中文标签（Windows 自动找黑体/微软雅黑）
- 半透明填充区分每个框

---

## JSON 最终输出格式

```json
{
  "image": {"width": 1920, "height": 1080},
  "objects": [
    {
      "name": "扫描枪1",
      "bbox": [120, 200, 320, 380],
      "color": "#FF4444",
      "iterations": [
        {"round": 1, "bbox": [100, 180, 340, 400], "feedback": "偏大"},
        {"round": 2, "bbox": [115, 195, 325, 385], "feedback": "右边界再收"},
        {"round": 3, "bbox": [120, 200, 320, 380], "feedback": "✅ 准确"}
      ]
    }
  ]
}
```

---

## 颜色方案

| 物体类别 | 框色 | 标签 |
|---------|------|------|
| 扫描枪 | 🔴 #FF4444 | 扫描枪1, 扫描枪2 |
| 护目镜 | 🔵 #4488FF | 护目镜1, 护目镜2 |
| 其他 | 🟢 #44BB44 | 自动轮转 |

---

## 中文字体

Windows 自动按序查找：黑体 → 微软雅黑 → 宋体 → 回退默认。
