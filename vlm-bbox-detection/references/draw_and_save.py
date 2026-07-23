#!/usr/bin/env python3
"""
Agent 视觉迭代标注 — 画框 + 存 JSON

用法:
    # 获取图片尺寸
    python draw_and_save.py --image input.jpg --get-size

    # 读取 JSON 画框（JSON 是 {prefix}_bbox.json 格式）
    python draw_and_save.py --image input.jpg --json input_bbox.json --output input_annotated.jpg --json-output input_bbox.json

    # 第一轮（从 JSON 字符串）
    python draw_and_save.py --image input.jpg --json '{"objects":[...]}' --output input_annotated.jpg --json-output input_bbox.json
"""

import json
import argparse
import sys
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# ─── 颜色方案（全自动轮转，不硬编码类别） ──────────────────────
COLOR_PALETTE = [
    ("#FF4444", "#CC0000"),  # Red
    ("#4488FF", "#0044CC"),  # Blue
    ("#44BB44", "#228822"),  # Green
    ("#FF8800", "#CC6600"),  # Orange
    ("#CC44CC", "#880088"),  # Purple
    ("#FFCC00", "#CC9900"),  # Yellow
    ("#44CCCC", "#228888"),  # Teal
    ("#FF6688", "#CC3355"),  # Pink
    ("#8866FF", "#5533CC"),  # Indigo
    ("#66CC88", "#339955"),  # Mint
]


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def find_chinese_font() -> str:
    """在 Windows 上查找可用的中文字体"""
    candidates = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simkai.ttf",
        "C:/Windows/Fonts/mingliu.ttc",
    ]
    for fp in candidates:
        if os.path.exists(fp):
            return fp
    return None


def get_image_size(image_path: str) -> dict:
    """获取图片尺寸"""
    img = Image.open(image_path)
    return {"width": img.width, "height": img.height, "path": str(Path(image_path).resolve())}


def normalize_name(raw_name: str, known_categories: list) -> tuple:
    """
    对齐物体名称到已知类别，返回 (category, display_name, index_in_category)
    - category: 标准化类别名（用于颜色匹配）
    - display_name: 展示名（如 "扫描枪1"）
    - index: 该类别的第几个
    """
    raw_lower = raw_name.strip().lower()
    for cat in known_categories:
        if cat.lower() in raw_lower:
            return cat, raw_name.strip(), None
    # 未知类别：尝试剥离尾部数字
    import re
    m = re.match(r"^(.+?)(\d+)$", raw_name.strip())
    if m:
        base, num = m.group(1).strip(), int(m.group(2))
        return base, f"{base}{num}", num - 1
    return raw_name.strip(), raw_name.strip(), None


def get_color_for_category(category: str, index: int, total: int) -> tuple:
    """为每个不同类别自动分配颜色（基于类别名的 hash），同类别微调色调"""
    cat_lower = category.lower()
    color_idx = hash(cat_lower) % len(COLOR_PALETTE)
    base_fill, base_outline = COLOR_PALETTE[color_idx]

    fill_rgb = hex_to_rgb(base_fill)
    outline_rgb = hex_to_rgb(base_outline)

    if total > 1 and index > 0:
        # 微调色调：每个子编号亮度略微偏移
        shift = min(index * 15, 60)
        fill_rgb = tuple(max(0, min(255, c - shift)) for c in fill_rgb)

    fill_hex = "#{:02X}{:02X}{:02X}".format(*fill_rgb)
    return fill_hex, hex_to_rgb(fill_hex), outline_rgb


def count_category_objects(objects: list) -> dict:
    """统计每个类别的物体数量"""
    from collections import Counter
    names = [obj.get("name", "").strip() for obj in objects]
    # 剥离数字做类别计数
    import re
    cats = []
    for n in names:
        m = re.match(r"^(.+?)(\d+)$", n)
        cats.append(m.group(1).strip() if m else n)
    return Counter(cats)


def draw_bboxes(
    image_path: str,
    objects: list,
    output_path: str,
    font_size: int = 24,
    line_width: int = 4,
    label_offset: int = 5,
) -> Image.Image:
    """
    在图片上画 bounding box 和中文标签

    Args:
        image_path: 原图路径
        objects: [{"name": "...", "bbox": [x1,y1,x2,y2]}, ...]
        output_path: 输出图片路径
        font_size: 标签字体大小
        line_width: 框线宽度
        label_offset: 标签离框的距离
    """
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 中文字体
    font_path = find_chinese_font()
    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    # 统计每个类别的物体数
    cat_counts = count_category_objects(objects)
    cat_indices = {}

    for obj in objects:
        name = obj.get("name", "unknown").strip()
        bbox = obj.get("bbox", [0, 0, 0, 0])

        # 确定类别和编号
        import re
        m = re.match(r"^(.+?)(\d+)$", name)
        base_name = m.group(1).strip() if m else name

        # 分配该类别内的序号
        if base_name not in cat_indices:
            cat_indices[base_name] = 0
        idx = cat_indices[base_name]
        cat_indices[base_name] += 1

        # 构建标签
        if cat_counts.get(base_name, 1) > 1:
            label_text = f"{base_name}{idx + 1}"
        else:
            label_text = name

        # 获取颜色
        fill_hex, fill_rgb, outline_rgb = get_color_for_category(base_name, idx, cat_counts.get(base_name, 1))

        # 画框
        x1, y1, x2, y2 = bbox
        draw.rectangle([x1, y1, x2, y2], outline=outline_rgb, width=line_width)

        # 画半透明填充（微弱）
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([x1, y1, x2, y2], fill=(*fill_rgb, 40))
        img_rgba = img.convert("RGBA")
        img_rgba = Image.alpha_composite(img_rgba, overlay)
        img = img_rgba.convert("RGB")
        draw = ImageDraw.Draw(img)

        # 重画框线（因为覆盖了）
        draw.rectangle([x1, y1, x2, y2], outline=outline_rgb, width=line_width)

        # 标签背景
        try:
            bbox_text = draw.textbbox((0, 0), label_text, font=font)
        except AttributeError:
            # PIL < 8.0 fallback
            tw, th = draw.textsize(label_text, font=font)
            bbox_text = (0, 0, tw, th)
        text_w = bbox_text[2] - bbox_text[0]
        text_h = bbox_text[3] - bbox_text[1]

        label_x = x1
        label_y = y1 - text_h - label_offset
        if label_y < 0:
            label_y = y2 + label_offset

        # 标签背景
        draw.rectangle(
            [label_x - 2, label_y - 2, label_x + text_w + 2, label_y + text_h + 2],
            fill=outline_rgb,
        )
        # 标签文字
        draw.text((label_x, label_y), label_text, fill=(255, 255, 255), font=font)

    img.save(output_path, quality=95)
    print(f"[draw_bboxes] 已保存标注图 → {output_path}")
    print(f"[draw_bboxes] 共标注 {len(objects)} 个物体")
    return img


def parse_vlm_json(vlm_response: str) -> list:
    """从 VLM 响应中提取 objects 列表"""
    # 尝试多种解析方式
    text = vlm_response.strip()

    # 方式1: 直接解析 JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "objects" in data:
            return data["objects"]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # 方式2: 提取 JSON 代码块
    import re
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if isinstance(data, dict) and "objects" in data:
                return data["objects"]
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # 方式3: 提取 { ... } 内容
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        try:
            data = json.loads(brace_match.group(0))
            if isinstance(data, dict) and "objects" in data:
                return data["objects"]
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从 VLM 响应中解析 JSON: {text[:200]}...")


def save_result_json(output_path: str, image_path: str, objects: list, iterations: int):
    """保存最终 JSON 结果"""
    img = Image.open(image_path)
    result = {
        "image": {
            "path": str(Path(image_path).resolve()),
            "width": img.width,
            "height": img.height,
        },
        "iterations": iterations,
        "objects": objects,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[save_result] JSON 已保存 → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Agent 视觉迭代标注工具")
    parser.add_argument("--image", required=True, help="输入图片路径")
    parser.add_argument("--get-size", action="store_true", help="仅获取图片尺寸")
    parser.add_argument("--json", help="JSON 文件路径 或 JSON 字符串")
    parser.add_argument("--output", default="annotated.jpg", help="标注图输出路径")
    parser.add_argument("--json-output", default="result.json", help="JSON 结果输出路径")
    args = parser.parse_args()

    # 获取尺寸
    if args.get_size:
        size = get_image_size(args.image)
        print(json.dumps(size, ensure_ascii=False))
        return

    if not os.path.exists(args.image):
        print(f"[ERROR] 图片不存在: {args.image}")
        sys.exit(1)

    # 加载 objects
    if args.json:
        if os.path.exists(args.json) and args.json.endswith(".json"):
            with open(args.json, "r", encoding="utf-8") as f:
                data = json.load(f)
                objects = data.get("objects", [])
                iterations = data.get("iterations", 0) + 1
        else:
            objects = parse_vlm_json(args.json)
            iterations = 1
    else:
        objects = []
        iterations = 0

    # 画框
    draw_bboxes(args.image, objects, args.output)

    # 存 JSON（自动递增轮次）
    save_result_json(args.json_output, args.image, objects, iterations)


if __name__ == "__main__":
    main()
