# VLM Prompt 模板

## 第一阶段：初始检测 Prompt

发给 VLM 之前，先获取图片尺寸（width, height），然后填入模板。

### 中文版

```
这张图片的尺寸是 {width} x {height} 像素。

请你在图片中找出所有的「{target_objects}」，并给出每个物体的精确 bounding box 坐标。

请严格按照以下 JSON 格式返回，不要添加任何解释或额外文字：

{
  "objects": [
    {"name": "扫描枪1", "bbox": [x1, y1, x2, y2]},
    {"name": "护目镜1", "bbox": [x1, y1, x2, y2]}
  ]
}

重要规则：
1. 坐标是像素坐标，x1,y1 是左上角，x2,y2 是右下角
2. 所有坐标必须在 0~{width}（x轴）和 0~{height}（y轴）范围内
3. 如果某个物体有多个实例，请分别列出并在名称后编号（如"扫描枪1"、"扫描枪2"）
4. 如果没有找到某个物体，不要列出它
5. 只输出 JSON，不要输出任何其他文字
```

### English version

```
This image is {width} x {height} pixels.

Please locate all "{target_objects}" in the image and provide precise bounding box coordinates for each instance.

Return ONLY a JSON object in this exact format, no other text:

{
  "objects": [
    {"name": "barcode scanner1", "bbox": [x1, y1, x2, y2]},
    {"name": "safety goggles1", "bbox": [x1, y1, x2, y2]}
  ]
}

Rules:
1. Coordinates are pixel coordinates. x1,y1 = top-left corner, x2,y2 = bottom-right corner
2. All coordinates must be within 0~{width} (x) and 0~{height} (y)
3. For multiple instances of the same object, number them (e.g., "barcode scanner1", "barcode scanner2")
4. If an object is not present, omit it
5. Output ONLY the JSON — no explanations
```

---

## 第二阶段：验证与调整 Prompt

将画好框的图片发给 VLM。

### 中文版

```
这张图片上我已经画了 {n} 个 bounding box 标注框。

请你逐个检查每个标注框是否**精确**包围了目标物体。

对于每个框，你必须给出以下判断：

{
  "all_correct": false,
  "adjustments": [
    {
      "name": "扫描枪1",
      "current_bbox": [120, 200, 320, 380],
      "accurate": false,
      "whats_wrong": "框的右边界没有完全包住扫描枪的枪头部分",
      "direction": "向右扩展",
      "pixels": 20,
      "new_bbox": [120, 200, 340, 380]
    }
  ]
}

调整方向可选值：向上/下/左/右移动、扩大、缩小、向左/右/上/下扩展

重要：
1. 如果所有框都准确，"all_correct" 设为 true，"adjustments" 为空数组 []
2. 如果有任何框需要调整，"all_correct" 必须为 false
3. new_bbox 是基于调整后的完整新坐标
4. 对于准确的框，在 adjustments 中也要列出，但 accurate 设为 true，不填 new_bbox
5. 只输出 JSON，不要解释
```

### English version

```
I've drawn {n} bounding boxes on this image.

Please inspect each box and determine if it ACCURATELY encloses the target object.

Return your assessment as JSON:

{
  "all_correct": false,
  "adjustments": [
    {
      "name": "barcode scanner1",
      "current_bbox": [120, 200, 320, 380],
      "accurate": false,
      "whats_wrong": "Right edge doesn't fully enclose the scanner head",
      "direction": "expand right",
      "pixels": 20,
      "new_bbox": [120, 200, 340, 380]
    }
  ]
}

Direction values: move up/down/left/right, expand, shrink, expand left/right/up/down

Important:
1. If ALL boxes are perfect, set "all_correct": true and "adjustments": []
2. If ANY box needs fixing, "all_correct" MUST be false
3. new_bbox is the complete new coordinate after adjustment
4. For accurate boxes, still list them but set "accurate": true, no new_bbox
5. Output ONLY JSON
```

---

## 迭代记录模板

Agent 在每轮迭代中应输出如下格式的记录：

```
### 第 {N} 轮迭代

**VLM 描述：**
- 扫描枪1：位于图片左下角，约在 x:100-350, y:200-400 区域
- 护目镜1：位于图片右上角桌面上，约在 x:500-700, y:150-300 区域

**当前 bbox：**
- 扫描枪1: [120, 200, 320, 380]
- 护目镜1: [510, 160, 690, 290]

**VLM 反馈：**
- 扫描枪1：❌ 右边界偏左，未包住枪头 → **向右扩展 20px**
- 护目镜1：✅ 准确

**调整后：**
- 扫描枪1: [120, 200, 340, 380]  ← 变动
- 护目镜1: [510, 160, 690, 290]  ← 不变

状态：继续下一轮 / ✅ 全部完成
```
