#!/usr/bin/env python3
"""测试步骤解析"""
import sys
import os
import zipfile
import re

# 读取ZIP文件
with zipfile.ZipFile('/tmp/repo.zip', 'r') as zip_ref:
    content = zip_ref.read('HowToCook-master/dishes/vegetable_dish/蚝油三鲜菇/蚝油三鲜菇.md').decode('utf-8')

print("=" * 60)
print("测试步骤解析")
print("=" * 60)

# 查找"操作"部分的内容
print("\n查找 '## 操作' 部分...")
steps_section_match = re.search(r'## 操作\s*\n((?:[-*] .*\n?)*?(?=\n## |\Z))', content, re.IGNORECASE)

if steps_section_match:
    print("匹配成功！")
    steps_content = steps_section_match.group(1)
    print(f"内容长度: {len(steps_content)}")

    lines = steps_content.split('\n')
    print(f"行数: {len(lines)}")

    print("\n前 10 行:")
    for i, line in enumerate(lines[:10]):
        print(f"  {i+1}. {repr(line)}")

    steps = []
    for idx, line in enumerate(lines):
        line = line.strip()
        # 支持 - 和 * 两种列表标记
        if line.startswith('- ') or line.startswith('* '):
            step_content = line[2:].strip()  # 移除列表标记
            if step_content:
                steps.append({
                    'step': idx + 1,
                    'content': step_content
                })

    print(f"\n提取的步骤数: {len(steps)}")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
else:
    print("匹配失败！")

print("\n" + "=" * 60)
