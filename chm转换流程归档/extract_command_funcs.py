#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
README 生成辅助脚本 —— 第一步：提取所有命令的功能描述

用途：遍历所有 depth-3 文件夹，提取每条命令的"命令功能"段，
      为后续生成 README.md 提供数据基础。

此脚本仅用于数据收集，不直接生成 README。
"""

import os, re

base = r"C:\Users\chenjinyu\Desktop\机器学习\tmp\命令参考_文件夹"

def get_func_lines(filepath):
    """从命令文件中提取'命令功能'段的内容"""
    try:
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
                # 遇到下一个章节标题就停止
                if stripped in ('命令格式', '参数说明', '视图', '缺省级别', '使用指南', '使用实例'):
                    break
                if stripped:
                    func_lines.append(stripped)
        return ' '.join(func_lines)
    except:
        return ''

def collect_all():
    """遍历所有 depth-3 文件夹，收集命令信息"""
    result = {}
    for root, dirs, files in os.walk(base):
        depth = root.replace(base, '').count(os.sep)
        if depth == 3:
            folder_name = os.path.basename(root)
            txt_files = sorted([f for f in os.listdir(root) 
                               if f.endswith('.txt') and f != '_说明.txt'])
            commands = []
            for tf in txt_files:
                name = tf.replace('.txt', '')
                func = get_func_lines(os.path.join(root, tf))
                commands.append({'name': name, 'func': func})
            result[folder_name] = commands
            print(f"{folder_name}: {len(commands)} commands")
    return result

if __name__ == '__main__':
    data = collect_all()
    print(f"\nTotal folders: {len(data)}")
