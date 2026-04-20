#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版前端页面扫描器
"""

import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from frontend_page_scanner import FrontendPageScanner


def test_cloudwizard():
    """测试 CloudWizard.tsx 文件"""
    print("=" * 60)
    print("测试增强版扫描器 - CloudWizard.tsx")
    print("=" * 60)

    project_path = "/home/ws8634/programe/Compute.Tower-main"
    output_dir = str(project_root)

    scanner = FrontendPageScanner()
    result = scanner.scan(
        project_path=project_path,
        include_patterns=["**/*.tsx", "**/*.ts"],
        exclude_patterns=["node_modules/**", "dist/**", "build/**", "*.d.ts"],
        max_files=500,
        output_dir=output_dir
    )

    if not result.get('success', False):
        print(f"扫描失败: {result.get('error', '未知错误')}")
        print(f"错误类型: {result.get('error_type', '未知')}")
        print(f"堆栈: {result.get('traceback', '无')}")
        return result

    data = result.get('data', {})

    print(f"\n【扫描统计】")
    stats = data.get('statistics', {})
    print(f"  扫描文件: {stats.get('totalFiles', 0)} 个")
    print(f"  按钮: {stats.get('totalButtons', 0)} 个")
    print(f"  表单: {stats.get('totalForms', 0)} 个")
    print(f"  步骤: {stats.get('totalSteps', 0)} 个")
    print(f"  API调用: {stats.get('totalApiCalls', 0)} 个")
    print(f"  操作链: {stats.get('totalOperationChains', 0)} 个")

    print(f"\n【详细表单信息】")
    forms = data.get('forms', [])
    print(f"  找到 {len(forms)} 个表单")
    for idx, form in enumerate(forms):
        print(f"\n  表单 {idx + 1}: {form.get('name', 'unnamed')}")
        print(f"    实例: {form.get('form_instance', 'N/A')}")
        print(f"    位置: {form.get('file_path', 'N/A')}:{form.get('location', {}).get('start_line', 'N/A')}")
        print(f"    布局: {form.get('layout', 'vertical')}")
        print(f"    字段数: {len(form.get('fields', []))}")
        fields = form.get('fields', [])
        if fields:
            print(f"    字段:")
            for field in fields[:10]:
                required = '(必填)' if field.get('required', False) else ''
                print(f"      - {field.get('name', 'N/A')} ({field.get('label', 'N/A')}): {field.get('type', 'N/A')} {required}")
            if len(fields) > 10:
                print(f"      ... 还有 {len(fields) - 10} 个字段")

    print(f"\n【详细步骤信息】")
    steps = data.get('steps', [])
    print(f"  找到 {len(steps)} 个步骤")
    for idx, step in enumerate(steps):
        print(f"\n  步骤 {idx + 1}: {step.get('title', 'unnamed')}")
        print(f"    向导名称: {step.get('wizard_name', 'N/A')}")
        print(f"    步骤索引: {step.get('step_index', 'N/A')}")
        print(f"    文件: {step.get('file_path', 'N/A')}:{step.get('location', {}).get('start_line', 'N/A')}")
        print(f"    下一步: {step.get('next_step', '无')}")
        print(f"    上一步: {step.get('prev_step', '无')}")
        if step.get('buttons_in_step'):
            print(f"    相关按钮函数: {step['buttons_in_step']}")
        if step.get('form_fields_in_step'):
            print(f"    相关字段数: {len(step['form_fields_in_step'])} 个")

    print(f"\n【详细按钮信息】(前15个)")
    buttons = data.get('buttons', [])
    print(f"  找到 {len(buttons)} 个按钮")
    for idx, button in enumerate(buttons[:15]):
        print(f"\n  按钮 {idx + 1}: {button.get('text_content', 'unnamed')}")
        print(f"    类型: {button.get('type', 'N/A')}")
        print(f"    动作类型: {button.get('action_type', 'N/A')}")
        print(f"    onClick: {button.get('onClick', 'N/A')}")
        print(f"    文件: {button.get('file_path', 'N/A')}:{button.get('location', {}).get('start_line', 'N/A')}")

    print(f"\n【详细操作链信息】")
    chains = data.get('operationChains', [])
    print(f"  找到 {len(chains)} 个操作链")
    for idx, chain in enumerate(chains):
        print(f"\n  操作链 {idx + 1}: {chain.get('name', 'unnamed')}")
        print(f"    类型: {chain.get('chainType', 'N/A')}")
        print(f"    步骤数: {len(chain.get('steps', []))}")
        steps = chain.get('steps', [])
        if steps:
            print(f"    操作步骤:")
            for step in steps:
                print(f"      [{step.get('order', 'N/A')}] {step.get('type', 'N/A')}: {step.get('description', 'N/A')}")

    return result


def test_multiple_files():
    """测试多个文件"""
    print("\n" + "=" * 60)
    print("测试多个文件扫描")
    print("=" * 60)

    project_path = "/home/ws8634/programe/Compute.Tower-main"
    output_dir = str(project_root)

    scanner = FrontendPageScanner()
    result = scanner.scan(
        project_path=project_path,
        scan_mode="full",
        output_dir=output_dir
    )

    if not result.get('success', False):
        print(f"扫描失败: {result.get('error', '未知错误')}")
        return result

    data = result.get('data', {})
    stats = data.get('statistics', {})

    print(f"\n【整体统计】")
    print(f"  扫描文件数: {stats.get('totalFiles', 0)}")
    print(f"  按钮: {stats.get('totalButtons', 0)} 个")
    print(f"  表单: {stats.get('totalForms', 0)} 个")
    print(f"  步骤: {stats.get('totalSteps', 0)} 个")
    print(f"  API调用: {stats.get('totalApiCalls', 0)} 个")
    print(f"  操作链: {stats.get('totalOperationChains', 0)} 个")

    nodes = data.get('nodes', [])
    edges = data.get('edges', [])
    print(f"\n【知识图谱】")
    print(f"  节点数: {len(nodes)}")
    print(f"  边数: {len(edges)}")

    output_path = Path(project_root) / "scan_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {output_path}")

    output_files = data.get('output_files', {})
    if output_files.get('visualizer'):
        print(f"可视化页面已保存到: {output_files['visualizer']}")
    if output_files.get('json'):
        print(f"JSON结果已保存到: {output_files['json']}")

    return result


if __name__ == "__main__":
    try:
        result1 = test_cloudwizard()
        result2 = test_multiple_files()
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
    except Exception as e:
        import traceback
        print(f"测试失败: {e}")
        traceback.print_exc()
        sys.exit(1)
