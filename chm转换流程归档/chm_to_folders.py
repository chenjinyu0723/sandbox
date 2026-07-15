#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 CHM 解包后的 .hhc 目录树解析出来，
按照层级创建文件夹，把每个 HTML 页面提取纯文本后放入对应位置。
"""

import os, re, html, shutil, sys
from html.parser import HTMLParser
from pathlib import Path

# ========== 配置 ==========
CHM_EXTRACTED_DIR = Path(r"C:\Users\chenjinyu\Desktop\机器学习\tmp\chm_extracted")
OUTPUT_DIR = Path(r"\\?\C:\Users\chenjinyu\Desktop\机器学习\tmp\命令参考_文件夹")

# ========== 解析 .hhc ==========

def parse_hhc_structure(hhc_path):
    """用状态机解析 HHC 文件，正确处理 UL/LI 嵌套"""
    with open(hhc_path, 'r', encoding='gb2312', errors='replace') as f:
        content = f.read()
    
    entries = []
    
    # 找到所有的 <UL>, </UL>, <LI><OBJECT>...</OBJECT> 
    # 使用位置跟踪
    
    # 先提取所有 UL 标签的位置和类型
    ul_events = []
    for m in re.finditer(r'<(/?)[Uu][Ll][>\s]', content):
        tag = m.group(0).lower()
        is_close = '/' in tag
        ul_events.append((m.start(), -1 if is_close else 1))
    
    # 提取所有 OBJECT 块
    obj_pattern = re.compile(
        r'<OBJECT[^>]*>.*?</OBJECT>',
        re.IGNORECASE | re.DOTALL
    )
    
    for m in obj_pattern.finditer(content):
        block = m.group(0)
        obj_start = m.start()
        
        # 确定深度：数在这个 OBJECT 之前有多少个打开的 <UL>
        depth = 0
        for pos, delta in ul_events:
            if pos < obj_start:
                depth += delta
        
        # 提取 Name 和 Local
        name_match = re.search(r'name="Name"\s+value="([^"]*)"', block, re.IGNORECASE)
        local_match = re.search(r'name="Local"\s+value="([^"]*)"', block, re.IGNORECASE)
        
        if name_match and local_match:
            entries.append({
                'name': name_match.group(1),
                'local': local_match.group(1),
                'depth': depth
            })
        elif name_match:
            entries.append({
                'name': name_match.group(1),
                'local': '',
                'depth': depth
            })
    
    return entries


# ========== HTML 文本提取 ==========

class HTMLTextExtractor(HTMLParser):
    # 自闭合标签（HTMLParser 不会对这些调用 handle_endtag）
    SELF_CLOSING = {'meta', 'link', 'br', 'hr', 'img', 'input', 'base', 'area', 'col', 'embed', 'source', 'track', 'wbr'}
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'head', 'meta', 'link', 'noscript'}
        self.skip_depth = 0
        
    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            self.skip_depth += 1
        if tag_lower in ('br', 'p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'pre'):
            if self.skip_depth == 0:
                self.text_parts.append('\n')
        # 自闭合标签：立即回退 skip_depth
        if tag_lower in self.SELF_CLOSING and tag_lower in self.skip_tags:
            if self.skip_depth > 0:
                self.skip_depth -= 1
        
    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            if self.skip_depth > 0:
                self.skip_depth -= 1
        if tag_lower in ('p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            if self.skip_depth == 0:
                self.text_parts.append('\n')
        
    def handle_data(self, data):
        if self.skip_depth == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)
                
    def handle_entityref(self, name):
        if self.skip_depth == 0:
            self.text_parts.append('&' + name + ';')
            
    def handle_charref(self, name):
        if self.skip_depth == 0:
            self.text_parts.append('&#' + name + ';')

def extract_text_from_html(html_path):
    try:
        for encoding in ['gb2312', 'gbk', 'gb18030', 'utf-8', 'latin-1']:
            try:
                with open(html_path, 'r', encoding=encoding, errors='strict') as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            with open(html_path, 'r', encoding='gb2312', errors='replace') as f:
                content = f.read()
        
        content = html.unescape(content)
        extractor = HTMLTextExtractor()
        extractor.feed(content)
        raw_text = ''.join(extractor.text_parts)
        
        lines = raw_text.split('\n')
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            stripped = line.strip()
            if stripped:
                cleaned_lines.append(stripped)
                prev_empty = False
            elif not prev_empty:
                cleaned_lines.append('')
                prev_empty = True
        
        return '\n'.join(cleaned_lines).strip()
    except Exception as e:
        return f"[无法提取文本: {e}]"


# ========== 文件名安全化 ==========

def safe_filename(name, max_len=40):
    unsafe_chars = r'[\\/:*?"<>|]'
    name = re.sub(unsafe_chars, '_', name)
    name = name.strip(' .')
    if not name:
        name = '(空标题)'
    if len(name) > max_len:
        name = name[:max_len-3] + '...'
    return name


# ========== 主流程 ==========

def main():
    hhc_files = list(CHM_EXTRACTED_DIR.glob('*.hhc'))
    if not hhc_files:
        print("错误：未找到 .hhc 文件")
        return
    
    hhc_path = hhc_files[0]
    print(f"解析目录文件: {hhc_path}")
    
    entries = parse_hhc_structure(hhc_path)
    print(f"共找到 {len(entries)} 个条目")
    
    from collections import Counter
    depth_counts = Counter(e['depth'] for e in entries)
    print(f"深度分布: {dict(sorted(depth_counts.items()))}")
    
    for e in entries[:20]:
        indent = '  ' * max(0, e['depth'] - 1)
        print(f"{indent}[d={e['depth']}] {e['name'][:60]}")
    
    # 清理输出目录
    out_str = str(OUTPUT_DIR)
    bare = out_str[4:] if out_str.startswith(r'\\?\ ') else out_str
    if os.path.exists(bare):
        shutil.rmtree(bare)
    os.makedirs(out_str, exist_ok=True)
    
    # 路径栈
    path_stack = [out_str]
    
    folder_count = 0
    file_count = 0
    error_count = 0
    
    for idx, entry in enumerate(entries):
        depth = entry['depth']
        name = entry['name']
        local = entry['local']
        
        has_children = (idx + 1 < len(entries) and entries[idx + 1]['depth'] > depth)
        
        # 维护路径栈
        while len(path_stack) > depth:
            path_stack.pop()
        while len(path_stack) < depth:
            path_stack.append(path_stack[-1])
        
        parent_dir = path_stack[-1]
        safe_name = safe_filename(name)
        
        if has_children:
            folder_path = os.path.join(parent_dir, safe_name)
            try:
                os.makedirs(folder_path, exist_ok=True)
                folder_count += 1
            except OSError as e:
                print(f"  创建失败 [{safe_name}]: {e}")
                continue
            
            if len(path_stack) <= depth:
                path_stack.append(folder_path)
            else:
                path_stack[depth - 1] = folder_path
                if len(path_stack) > depth:
                    path_stack[depth] = folder_path
            
            if local:
                html_path = CHM_EXTRACTED_DIR / local
                if html_path.exists():
                    text_content = extract_text_from_html(str(html_path))
                    if text_content.strip():
                        try:
                            readme_path = os.path.join(folder_path, '_说明.txt')
                            with open(readme_path, 'w', encoding='utf-8') as f:
                                f.write(text_content)
                        except OSError:
                            pass
        else:
            if local:
                html_path = CHM_EXTRACTED_DIR / local
                if html_path.exists():
                    text_content = extract_text_from_html(str(html_path))
                    if text_content.strip():
                        try:
                            txt_path = os.path.join(parent_dir, safe_name + '.txt')
                            with open(txt_path, 'w', encoding='utf-8') as f:
                                f.write(text_content)
                            file_count += 1
                        except OSError:
                            pass
                else:
                    error_count += 1
    
    print(f"\n========== 完成 ==========")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"文件夹数: {folder_count}")
    print(f"文本文件数: {file_count}")
    print(f"缺失文件数: {error_count}")

if __name__ == '__main__':
    main()
