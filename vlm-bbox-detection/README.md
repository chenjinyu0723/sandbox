# VLM Iterative Bounding Box Detection

利用 VLM（Qwen-VL / GPT-4V / Claude）进行迭代式目标检测和标注。

## 工作流

```
读图获取尺寸 → Prompt VLM 给出 bbox → 画框 + 存 JSON → 验证反馈 → 迭代调整 → 完成
```

## 文件

| 文件 | 说明 |
|------|------|
| `SKILL.md` | Hermes Agent Skill 文档 |
| `references/draw_and_save.py` | 画框 + 存 JSON 工具脚本 |
| `references/prompt_templates.md` | 中英文 Prompt 模板 |

## Quick Start

```bash
# 获取图片尺寸
python references/draw_and_save.py --image test.jpg --get-size

# 画框 + 存 JSON
python references/draw_and_save.py \
  --image test.jpg \
  --json '{"objects":[{"name":"扫描枪1","bbox":[100,200,300,400]}]}' \
  --output annotated.jpg \
  --json-output result.json
```

## 特性

- ✅ 中文标签支持（自动查找 Windows 中文字体）
- ✅ 相同物体自动编号（扫描枪1、扫描枪2...）
- ✅ 不同类别不同颜色
- ✅ 迭代调整历史记录
- ✅ JSON 输出含完整迭代轨迹
