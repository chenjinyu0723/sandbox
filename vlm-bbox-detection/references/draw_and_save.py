#!/usr/bin/env python3
"""
VLM 迭代标注 — 画框 + 存 JSON + 验证反馈工具

用法:
    # Step 1: 获取图片尺寸
    python draw_and_save.py --image input.jpg --get-size

    # Step 3: 画框 + 存 JSON（交互模式，边画边迭代）
    python draw_and_save.py --image input.jpg --json '{"objects":[...]}' --output annotated.jpg --json-output result.json

    # Step 4: 应用调整（输入 VLM 返回的调整 JSON）
    python draw_and_save.py --image input.jpg --json result.json --adjustments '[...]' --output annotated_v2.jpg --json-output result_v2.json
"""

import json
import argparse
import sys
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# ─── 颜色方案 ───────────────────────────────────────────────
CATEGORY_COLORS = {
    "扫描枪": ("#FF4444", "#CC0000"),
    "barcode scanner": ("#FF4444", "#CC0000"),
    "护目镜": ("#4488FF", "#0044CC"),
    "safety goggles": ("#4488FF", "#0044CC"),
    "安全帽": ("#FF8800", "#CC6600"),
    "helmet": ("#FF8800", "#CC6600"),
    "手套": ("#44BB44", "#228822"),
    "gloves": ("#44BB44", "#228822"),
}
FALLBACK_COLORS = [
    ("#FF4444", "#CC0000"),  # Red
    ("#4488FF", "#0044CC"),  # Blue
    ("#44BB44", "#228822"),  # Green
    ("#FF8800", "#CC6600"),  # Orange
    ("#CC44CC", "#880088"),  # Purple
    ("#FFCC00", "#CC9900"),  # Yellow
    ("#44CCCC", "#228888"),  # Teal
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
    """为类别获取颜色，同一类别不同编号微调色调"""
    cat_lower = category.lower()
    if cat_lower in CATEGORY_COLORS:
        base_fill, base_outline = CATEGORY_COLORS[cat_lower]
    else:
        # 回退到轮转颜色
        color_idx = hash(cat_lower) % len(FALLBACK_COLORS)
        base_fill, base_outline = FALLBACK_COLORS[color_idx]

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


def apply_adjustments(objects: list, adjustments: list) -> list:
    """根据 VLM 的调整建议更新 bbox"""
    updated = []
    for obj in objects:
        name = obj.get("name", "")
        bbox = list(obj.get("bbox", [0, 0, 0, 0]))
        color = obj.get("color", "")
        history = obj.get("iteration_history", [])

        # 查找是否有针对此物体的调整
        adj = None
        for a in adjustments:
            if a.get("name", "").strip() == name.strip():
                adj = a
                break

        if adj and adj.get("new_bbox"):
            old_bbox = list(bbox)
            bbox = adj["new_bbox"]
            history.append({
                "round": len(history) + 1,
                "bbox_before": old_bbox,
                "bbox_after": list(bbox),
                "vlm_feedback": adj.get("direction", "") + f" ({adj.get('pixels', '?')}px)",
            })

        updated.append({
            "name": name,
            "bbox": list(bbox),
            "color": color,
            "iteration_history": history,
        })

    return updated


def save_result_json(output_path: str, image_path: str, objects: list, prompt_objects: list, iterations: int):
    """保存最终 JSON 结果"""
    img = Image.open(image_path)
    result = {
        "image": {
            "path": str(Path(image_path).resolve()),
            "width": img.width,
            "height": img.height,
        },
        "prompt_objects": prompt_objects,
        "iterations": iterations,
        "objects": objects,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[save_result] JSON 已保存 → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="VLM 迭代标注工具")
    parser.add_argument("--image", required=True, help="输入图片路径")
    parser.add_argument("--get-size", action="store_true", help="仅获取图片尺寸")
    parser.add_argument("--json", help="VLM 返回的 JSON 字符串或已有 JSON 文件路径")
    parser.add_argument("--output", default="annotated.jpg", help="标注图输出路径")
    parser.add_argument("--json-output", default="result.json", help="JSON 结果输出路径")
    parser.add_argument("--adjustments", help="VLM 返回的调整建议 JSON")
    parser.add_argument("--prompt-objects", default="", help="要检测的物体列表，逗号分隔")
    parser.add_argument("--iterations", type=int, default=1, help="当前迭代轮次")
    args = parser.parse_args()

    # Step 1: 获取尺寸
    if args.get_size:
        size = get_image_size(args.image)
        print(json.dumps(size, ensure_ascii=False))
        return

    # 检查图片存在
    if not os.path.exists(args.image):
        print(f"[ERROR] 图片不存在: {args.image}")
        sys.exit(1)

    # Step 3/4: 画框
    prompt_objects = [o.strip() for o in args.prompt_objects.split(",") if o.strip()] if args.prompt_objects else []

    # 加载 objects
    if args.json:
        if os.path.exists(args.json) and args.json.endswith(".json"):
            with open(args.json, "r", encoding="utf-8") as f:
                data = json.load(f)
                objects = data.get("objects", [])
                if not prompt_objects:
                    prompt_objects = data.get("prompt_objects", [])
                iterations = data.get("iterations", 0) + 1
        else:
            objects = parse_vlm_json(args.json)
            iterations = args.iterations
    else:
        objects = []
        iterations = 0

    # 应用调整
    if args.adjustments:
        try:
            adj_data = json.loads(args.adjustments)
            adjustments = adj_data.get("adjustments", []) if isinstance(adj_data, dict) else adj_data
            objects = apply_adjustments(objects, adjustments)
        except json.JSONDecodeError:
            print("[WARN] 无法解析 adjustments JSON，跳过调整")

    # 画框
    draw_bboxes(args.image, objects, args.output)

    # 存 JSON
    save_result_json(args.json_output, args.image, objects, prompt_objects, iterations)


if __name__ == "__main__":
    main()
