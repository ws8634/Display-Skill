#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端页面扫描工具
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frontend_page_scanner import FrontendPageScanner


def test_scanner():
    """测试扫描器"""
    print("=" * 60)
    print("前端页面扫描测试")
    print("=" * 60)

    scanner = FrontendPageScanner()

    project_path = "/home/ws8634/programe/Compute.Tower-main"

    print(f"\n目标项目: {project_path}")
    print("正在扫描...")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_results")

    result = scanner.scan(
        project_path=project_path,
        scan_mode="full",
        output_format="both",
        include_patterns=["**/*.tsx", "**/*.ts"],
        exclude_patterns=["node_modules/**", "dist/**", "build/**", "*.d.ts"],
        max_files=50,
        output_dir=output_dir
    )

    if not result["success"]:
        print(f"\n❌ 扫描失败: {result.get('error')}")
        if result.get('traceback'):
            print(f"\n详细错误:\n{result['traceback']}")
        return False

    data = result["data"]
    summary = result["summary"]

    print("\n" + "=" * 60)
    print("扫描结果")
    print("=" * 60)

    print(f"\n📊 统计信息:")
    print(f"  - 扫描文件数: {summary.get('total_files_scanned', 0)}")
    print(f"  - 按钮数量: {summary.get('total_buttons', 0)}")
    print(f"  - 表单数量: {summary.get('total_forms', 0)}")
    print(f"  - 步骤数量: {summary.get('total_steps', 0)}")
    print(f"  - API调用: {summary.get('total_api_calls', 0)}")
    print(f"  - 操作链: {summary.get('total_operation_chains', 0)}")

    output_files = data.get("output_files", {})

    if output_files.get("json"):
        print(f"\n💾 JSON输出: {output_files['json']}")

    if output_files.get("visualizer"):
        print(f"🌐 可视化页面: {output_files['visualizer']}")

    buttons = data.get("buttons", [])
    if buttons:
        print(f"\n🔘 按钮示例 (前5个):")
        for btn in buttons[:5]:
            print(f"  - [{btn.get('type')}] {btn.get('name')} ({btn.get('action_type')})")
            print(f"    onClick: {btn.get('onClick')}")
            print(f"    文件: {btn.get('file_path')}:{btn.get('location', {}).get('start_line')}")
            print()

    forms = data.get("forms", [])
    if forms:
        print(f"\n📝 表单示例 (前3个):")
        for form in forms[:3]:
            field_count = len(form.get("fields", []))
            print(f"  - {form.get('name')} ({field_count} 个字段)")
            print(f"    表单实例: {form.get('form_instance')}")
            print(f"    文件: {form.get('file_path')}")
            print()

    chains = data.get("operation_chains", [])
    if chains:
        print(f"\n⛓️ 操作链示例 (前3个):")
        for chain in chains[:3]:
            steps = chain.get("steps", [])
            print(f"  - {chain.get('name')} ({len(steps)} 个步骤)")
            print(f"    组件: {chain.get('component_name')}")
            for step in steps:
                print(f"      → {step.get('type')}: {step.get('description', '-')}")
            print()

    print("\n" + "=" * 60)
    print("✅ 扫描完成!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_scanner()
    sys.exit(0 if success else 1)
