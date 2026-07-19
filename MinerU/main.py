# MinerU DOCX/PPTX → Markdown converter
#   with optional LLM-powered image description
#
# Usage:
#   python main.py path/to/file.docx
#   python main.py path/to/file.pptx -o out.md
#   python main.py path/to/file.docx --no-llm     # skip LLM

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════
#  config
# ═══════════════════════════════════════════════════════════

def _load_config(config_path=None):
    path = Path(config_path) if config_path else (_PROJECT_ROOT / "config.yaml")
    if not path.exists():
        return {}
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: config read failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════
#  paths
# ═══════════════════════════════════════════════════════════

def _mk_paths(input_path, output, images_dir):
    f = Path(input_path).resolve()
    stem = f.stem
    if output:
        md = Path(output).resolve()
        base = md.parent
    else:
        base = f.parent
        md = base / f"{stem}.md"
    if images_dir:
        d = Path(images_dir)
        if not d.is_absolute():
            d = base / d
    else:
        d = base / f"{stem}_images"
    return md, d


# ═══════════════════════════════════════════════════════════
#  conversion
# ═══════════════════════════════════════════════════════════

def _convert(file_bytes, image_writer, img_buket_path, ext):
    from io import BytesIO
    from mineru.backend.office.model_output_to_middle_json import result_to_middle_json
    from mineru.backend.office.mkcontent.output_builders import mk_blocks_to_markdown
    from mineru.utils.enum_class import MakeMode

    if ext == ".docx":
        from mineru.model.docx.main import convert_binary
    else:
        from mineru.model.pptx.main import convert_binary

    results = convert_binary(BytesIO(file_bytes))
    middle_json = result_to_middle_json(results, image_writer)
    pages = []
    for pi in middle_json["pdf_info"]:
        pages.extend(mk_blocks_to_markdown(
            pi.get("para_blocks", []), MakeMode.MM_MD,
            img_buket_path=img_buket_path,
            page_idx=pi.get("page_idx", 0),
        ))
    return "\n\n".join(pages)


# ═══════════════════════════════════════════════════════════
#  LLM image descriptions
# ═══════════════════════════════════════════════════════════

def _image_postprocess(img_dir, describer, seq_writer, markdown, img_buket_path):
    """Dedup images (SHA-256 of raw bytes = pixel-level comparison),
    call LLM once per unique image, then augment markdown.

    Returns (new_markdown, stats_dict).
    """
    if not img_dir.exists():
        return markdown, {}

    # ---- 1. 从 SequentialImageWriter 读取去重信息 ----
    # _hash_to_name: {content_sha256 → seq_name}  ← 同一个 SHA-256 =
    #   同一张图片（像素完全一致），只会写一次盘，也只调一次 LLM
    # _old_to_new:   {original_sha256_path → seq_name}  ← 用于路径替换
    unique_hashes = len(seq_writer._hash_to_name)          # 去重后的唯一图片数
    total_refs    = len(seq_writer._old_to_new)            # 文档中图片引用总数
    duplicates    = total_refs - unique_hashes

    print(f"  图片引用 {total_refs} 次，去重后唯一图片 {unique_hashes} 张"
          + (f"，跳过 {duplicates} 个重复引用" if duplicates > 0 else ""))

    # ---- 2. 按数字顺序收集唯一图片文件 ----
    unique_files = sorted(
        (f for f in img_dir.iterdir()
         if f.is_file() and f.suffix.lower() in
         {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}),
        key=lambda x: (
            int(m.group(1)) if (m := re.match(r"(\d+)", x.stem)) else 99999,
            x.name,
        ),
    )

    # ---- 3. LLM 逐张描述（每张唯一图片只调一次） ----
    desc_map = {}   # seq_name → description
    if describer is not None:
        total = len(unique_files)
        for idx, f in enumerate(unique_files, 1):
            print(f"  [{idx}/{total}] {f.name} ...", end=" ", flush=True)
            desc = describer.describe(str(f))
            if desc:
                desc_map[f.name] = desc.strip()
                print(f"✓ ({len(desc_map[f.name])} 字)")
            else:
                print("✗")
        if desc_map:
            print(f"  已描述 {len(desc_map)}/{total} 张图片")

    # ---- 4. 将描述注入 Markdown（同一张图的多次引用复用同一条描述） ----
    if desc_map:
        import re as _re
        def _replace(m):
            old_path = m.group(1)
            fname = old_path.rsplit("/", 1)[-1] if "/" in old_path else old_path
            desc = desc_map.get(fname, "")
            if desc:
                # 每条描述用 blockquote 包裹，以 > **图像说明** 领起，
                # 多行描述每行加 >  前缀，与上下正文形成清晰分隔
                lines = desc.split("\n")
                quoted = "\n".join(
                    f"> {line}" if line.strip() else ">"
                    for line in lines
                )
                return f"![]({old_path})\n\n> **图像说明**\n{quoted}"
            return m.group(0)
        markdown = _re.sub(r"!\[\]\(([^)]+)\)", _replace, markdown)

    stats = {
        "total_refs": total_refs,
        "unique": unique_hashes,
        "duplicates": duplicates,
        "described": len(desc_map),
    }
    return markdown, stats


# ═══════════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════════

def main():
    cfg = _load_config()
    llm_cfg = cfg.get("llm", {})

    p = argparse.ArgumentParser(description="DOCX/PPTX → Markdown (MinerU)")
    p.add_argument("input", help=".docx or .pptx path")
    p.add_argument("-o", "--output", help="output .md path")
    p.add_argument("--images-dir", help="images directory")
    p.add_argument("--no-images", action="store_true")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--config", help="config.yaml path")
    args = p.parse_args()

    # Re-read config if --config given
    if args.config:
        cfg = _load_config(args.config)
        llm_cfg = cfg.get("llm", {})

    input_path = args.input
    if not os.path.isfile(input_path):
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    ext = Path(input_path).suffix.lower()
    if ext not in (".docx", ".pptx"):
        print(f"Error: unsupported format '{ext}'")
        sys.exit(1)

    out_md, img_dir = _mk_paths(input_path, args.output, args.images_dir)

    with open(input_path, "rb") as f:
        file_bytes = f.read()

    # --- image writer ---
    seq_writer = None
    if args.no_images:
        image_writer = None
        img_buket_path = ""
    else:
        img_dir.mkdir(parents=True, exist_ok=True)
        from mineru.data.data_reader_writer.filebase import FileBasedDataWriter
        from mineru.backend.utils.seq_image_writer import SequentialImageWriter
        raw_writer = FileBasedDataWriter(str(img_dir))
        seq_writer = SequentialImageWriter(raw_writer)
        image_writer = seq_writer
        try:
            img_buket_path = str(img_dir.relative_to(out_md.parent))
        except ValueError:
            img_buket_path = str(img_dir)

    print(f"Converting {'DOCX' if ext=='.docx' else 'PPTX'}: {input_path}")
    print(f"  Output: {out_md}")
    if image_writer:
        print(f"  Images: {img_dir}/")

    # --- convert ---
    try:
        markdown = _convert(file_bytes, image_writer, img_buket_path, ext)
    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # --- patch SHA256 paths → sequential names ---
    if seq_writer:
        markdown = seq_writer.patch_markdown(markdown, img_buket_path)

    # --- LLM descriptions ---
    describer = None
    if image_writer and not args.no_llm:
        api_key = (llm_cfg.get("api_key", "") or "").strip()
        is_placeholder = any(w in api_key.lower() for w in (
            "your-api-key", "your_key", "xxx", "placeholder", "changeme",
            "your-", "sk-you",
        ))
        if api_key and not is_placeholder:
            try:
                from mineru.backend.utils.llm_client import LLMConfig, ImageDescriber
                describer = ImageDescriber(LLMConfig(
                    api_key=api_key,
                    base_url=llm_cfg.get("base_url", "https://api.openai.com/v1"),
                    model=llm_cfg.get("model", "gpt-4o"),
                    max_tokens=llm_cfg.get("max_tokens", 1500),
                    temperature=llm_cfg.get("temperature", 0.3),
                    system_prompt=llm_cfg.get("system_prompt", ""),
                    user_prompt=llm_cfg.get("user_prompt", "请描述这张图片的内容。"),
                ))
                print(f"\n[LLM] {llm_cfg['model']} @ {llm_cfg.get('base_url','')}")
            except Exception as e:
                print(f"Warning: LLM init failed: {e}")

    if seq_writer:
        markdown, img_stats = _image_postprocess(
            img_dir, describer, seq_writer, markdown, img_buket_path,
        )
    else:
        img_stats = {}

    # --- write ---
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown, encoding="utf-8")
    print(f"\nDone → {out_md}  ({len(markdown)} 字符)")


if __name__ == "__main__":
    main()
