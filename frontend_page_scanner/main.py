#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端页面扫描工具 (Frontend Page Scanner)
用于扫描前端TSX页面代码，识别按钮、表单、向导等交互元素，
构建操作链用于E2E测试用例生成。
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from .models.data_models import ScanResult
from .scanners.button_scanner import ButtonScanner
from .scanners.form_scanner import FormScanner
from .scanners.step_scanner import StepScanner
from .scanners.api_call_scanner import ApiCallScanner
from .builders.operation_chain_builder import OperationChainBuilder
from .utils.helpers import scan_project_files


class FrontendPageScanner:
    """前端页面扫描器"""

    def __init__(self):
        self.button_scanner = ButtonScanner()
        self.form_scanner = FormScanner()
        self.step_scanner = StepScanner()
        self.api_call_scanner = ApiCallScanner()
        self.chain_builder = OperationChainBuilder()

    def scan(
        self,
        project_path: str,
        scan_mode: str = "full",
        output_format: str = "json",
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        max_files: int = 500,
        output_dir: str = None
    ) -> Dict[str, Any]:
        """执行扫描

        Args:
            project_path: 目标项目路径
            scan_mode: 扫描模式 (full, buttons, forms, steps, api_calls, operation_chains)
            output_format: 输出格式 (json, visualizer, both)
            include_patterns: 包含的文件模式
            exclude_patterns: 排除的文件模式
            max_files: 最大扫描文件数
            output_dir: 输出目录

        Returns:
            扫描结果字典
        """
        try:
            if include_patterns is None:
                include_patterns = ["**/*.tsx", "**/*.ts"]
            if exclude_patterns is None:
                exclude_patterns = ["node_modules/**", "dist/**", "build/**", "*.d.ts"]

            files = scan_project_files(project_path, include_patterns, exclude_patterns, max_files)

            if not files:
                return {
                    "success": False,
                    "error": f"未找到匹配的文件，路径: {project_path}",
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns
                }

            result = ScanResult()
            result.files_scanned = files

            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    continue

                if scan_mode in ["full", "buttons"]:
                    buttons = self.button_scanner.scan_file(file_path, content)
                    result.buttons.extend(buttons)

                if scan_mode in ["full", "forms"]:
                    forms = self.form_scanner.scan_file(file_path, content)
                    result.forms.extend(forms)

                if scan_mode in ["full", "steps"]:
                    steps = self.step_scanner.scan_file(file_path, content)
                    result.steps.extend(steps)

                if scan_mode in ["full", "api_calls"]:
                    api_calls = self.api_call_scanner.scan_file(file_path, content)
                    result.api_calls.extend(api_calls)

                if scan_mode in ["full", "operation_chains"]:
                    file_buttons = [b for b in result.buttons if b.file_path == file_path]
                    file_forms = [f for f in result.forms if f.file_path == file_path]
                    file_steps = [s for s in result.steps if s.file_path == file_path]
                    file_api_calls = [a for a in result.api_calls if a.file_path == file_path]

                    if file_buttons or file_forms or file_steps or file_api_calls:
                        chains = self.chain_builder.build_chains(
                            file_buttons, file_forms, file_steps, file_api_calls,
                            file_path, content
                        )
                        result.operation_chains.extend(chains)

            result_dict = result.to_dict()

            output_files = {}

            if output_format in ["json", "both"]:
                json_output = self._save_json_result(result_dict, output_dir, project_path)
                output_files["json"] = json_output

            if output_format in ["visualizer", "both"]:
                visualizer_output = self._create_visualizer(result_dict, output_dir, project_path)
                output_files["visualizer"] = visualizer_output

            result_dict["output_files"] = output_files

            return {
                "success": True,
                "data": result_dict,
                "summary": result.get_summary()
            }

        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }

    def _save_json_result(
        self,
        result_dict: Dict[str, Any],
        output_dir: Optional[str],
        project_path: str
    ) -> str:
        """保存JSON结果到文件"""
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path(project_path) / "frontend_scan_results"

        output_path.mkdir(parents=True, exist_ok=True)

        json_file = output_path / "frontend_interaction_result.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)

        return str(json_file)

    def _create_visualizer(
        self,
        result_dict: Dict[str, Any],
        output_dir: Optional[str],
        project_path: str
    ) -> str:
        """创建可视化页面"""
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path(project_path) / "frontend_scan_results"

        output_path.mkdir(parents=True, exist_ok=True)

        visualizer_file = output_path / "frontend_interaction_viewer.html"

        visualizer_template = self._get_visualizer_template()

        json_str = json.dumps(result_dict, ensure_ascii=False, indent=2)
        html_content = visualizer_template.replace('{{SCAN_RESULT_JSON}}', json_str)

        with open(visualizer_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(visualizer_file)

    def _get_visualizer_template(self) -> str:
        """获取可视化页面模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>前端页面交互分析结果</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            text-align: center;
            color: white;
            padding: 30px 0;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .tabs {
            display: flex;
            gap: 5px;
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 12px 24px;
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .tab:hover { background: rgba(255,255,255,0.3); }
        .tab.active { background: white; color: #667eea; font-weight: 600; }
        .panel {
            display: none;
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .panel.active { display: block; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 12px;
            color: white;
            text-align: center;
        }
        .stat-card h3 { font-size: 2.5rem; margin-bottom: 5px; }
        .stat-card p { opacity: 0.9; font-size: 0.95rem; }
        .stat-card.blue { background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%); }
        .stat-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .stat-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .stat-card.yellow { background: linear-gradient(135deg, #f5af19 0%, #f12711 100%); }
        .stat-card.purple { background: linear-gradient(135deg, #8e2de2 0%, #4a00e0 100%); }
        .search-box {
            margin-bottom: 20px;
        }
        .search-box input {
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .search-box input:focus {
            outline: none;
            border-color: #667eea;
        }
        .card-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        .card {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        .card-title { font-size: 1.1rem; font-weight: 600; color: #333; }
        .card-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge-primary { background: #e3f2fd; color: #1565c0; }
        .badge-success { background: #e8f5e9; color: #2e7d32; }
        .badge-warning { background: #fff3e0; color: #ef6c00; }
        .badge-danger { background: #ffebee; color: #c62828; }
        .badge-info { background: #e0f7fa; color: #00838f; }
        .card-content { font-size: 14px; color: #666; }
        .card-content p { margin-bottom: 8px; }
        .card-content .label { font-weight: 500; color: #333; }
        .code-block {
            background: #282c34;
            color: #abb2bf;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Fira Code', monospace;
            font-size: 13px;
            overflow-x: auto;
            margin-top: 10px;
        }
        .file-path {
            font-family: 'Fira Code', monospace;
            font-size: 12px;
            color: #667eea;
            background: #f3f4ff;
            padding: 8px 12px;
            border-radius: 6px;
            margin-top: 10px;
        }
        .chain-card {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border: 2px solid #667eea30;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
        }
        .chain-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .chain-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #667eea;
        }
        .chain-steps { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        .chain-step {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 16px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .step-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
            font-size: 14px;
        }
        .icon-click { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .icon-form { background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%); }
        .icon-api { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .icon-nav { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .icon-modal { background: linear-gradient(135deg, #f5af19 0%, #f12711 100%); }
        .step-text { font-size: 13px; color: #333; }
        .arrow { font-size: 20px; color: #999; font-weight: bold; }
        .graph-container {
            width: 100%;
            height: 600px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            position: relative;
        }
        #cy {
            width: 100%;
            height: 100%;
        }
        .legend {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        .empty-state h3 { font-size: 1.2rem; margin-bottom: 10px; }
        .empty-state p { font-size: 0.95rem; }
        .section-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            display: inline-block;
        }
        .toggle-btn {
            padding: 8px 16px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            margin-bottom: 15px;
        }
        .toggle-btn:hover { background: #5568d3; }
        .detail-panel {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        .detail-panel.expanded { max-height: 1000px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>前端页面交互分析结果</h1>
            <p>基于代码扫描的按钮、表单、操作链可视化</p>
        </div>

        <div class="tabs">
            <button class="tab active" data-tab="overview">概览</button>
            <button class="tab" data-tab="buttons">按钮</button>
            <button class="tab" data-tab="forms">表单</button>
            <button class="tab" data-tab="steps">步骤向导</button>
            <button class="tab" data-tab="api-calls">API调用</button>
            <button class="tab" data-tab="chains">操作链</button>
            <button class="tab" data-tab="graph">知识图谱</button>
        </div>

        <div class="panel active" id="overview">
            <div class="stats">
                <div class="stat-card">
                    <h3 id="stat-files">0</h3>
                    <p>扫描文件数</p>
                </div>
                <div class="stat-card blue">
                    <h3 id="stat-buttons">0</h3>
                    <p>按钮数量</p>
                </div>
                <div class="stat-card green">
                    <h3 id="stat-forms">0</h3>
                    <p>表单数量</p>
                </div>
                <div class="stat-card orange">
                    <h3 id="stat-steps">0</h3>
                    <p>步骤数量</p>
                </div>
                <div class="stat-card yellow">
                    <h3 id="stat-apis">0</h3>
                    <p>API调用</p>
                </div>
                <div class="stat-card purple">
                    <h3 id="stat-chains">0</h3>
                    <p>操作链</p>
                </div>
            </div>

            <h2 class="section-title">最近操作链</h2>
            <div id="overview-chains"></div>
        </div>

        <div class="panel" id="buttons">
            <div class="search-box">
                <input type="text" placeholder="搜索按钮名称、类型或处理函数..." id="button-search">
            </div>
            <div class="card-list" id="button-list"></div>
        </div>

        <div class="panel" id="forms">
            <div class="search-box">
                <input type="text" placeholder="搜索表单名称或字段..." id="form-search">
            </div>
            <div class="card-list" id="form-list"></div>
        </div>

        <div class="panel" id="steps">
            <div class="card-list" id="steps-list"></div>
        </div>

        <div class="panel" id="api-calls">
            <div class="search-box">
                <input type="text" placeholder="搜索API路径或方法..." id="api-search">
            </div>
            <div class="card-list" id="api-list"></div>
        </div>

        <div class="panel" id="chains">
            <div id="chains-list"></div>
        </div>

        <div class="panel" id="graph">
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #667eea;"></div>
                    <span>按钮</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #2193b0;"></div>
                    <span>表单</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f093fb;"></div>
                    <span>API</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #11998e;"></div>
                    <span>步骤</span>
                </div>
            </div>
            <div class="graph-container">
                <div id="cy"></div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    <script>
        const scanData = {{SCAN_RESULT_JSON}};

        document.addEventListener('DOMContentLoaded', () => {
            initTabs();
            initOverview();
            initButtons();
            initForms();
            initSteps();
            initApiCalls();
            initChains();
            initGraph();
        });

        function initTabs() {
            const tabs = document.querySelectorAll('.tab');
            const panels = document.querySelectorAll('.panel');

            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    tabs.forEach(t => t.classList.remove('active'));
                    panels.forEach(p => p.classList.remove('active'));

                    tab.classList.add('active');
                    const tabName = tab.dataset.tab;
                    document.getElementById(tabName).classList.add('active');
                });
            });
        }

        function initOverview() {
            const summary = scanData.summary || {};
            document.getElementById('stat-files').textContent = summary.total_files_scanned || 0;
            document.getElementById('stat-buttons').textContent = summary.total_buttons || 0;
            document.getElementById('stat-forms').textContent = summary.total_forms || 0;
            document.getElementById('stat-steps').textContent = summary.total_steps || 0;
            document.getElementById('stat-apis').textContent = summary.total_api_calls || 0;
            document.getElementById('stat-chains').textContent = summary.total_operation_chains || 0;

            const chainsContainer = document.getElementById('overview-chains');
            const chains = scanData.operation_chains || [];

            if (chains.length === 0) {
                chainsContainer.innerHTML = '<div class="empty-state"><h3>暂无操作链数据</h3><p>扫描结果中没有检测到操作链</p></div>';
                return;
            }

            let html = '';
            chains.slice(0, 5).forEach(chain => {
                html += renderChainCard(chain);
            });
            chainsContainer.innerHTML = html;
        }

        function initButtons() {
            const buttons = scanData.buttons || [];
            const container = document.getElementById('button-list');

            if (buttons.length === 0) {
                container.innerHTML = '<div class="empty-state"><h3>暂无按钮数据</h3><p>扫描结果中没有检测到按钮</p></div>';
                return;
            }

            let html = '';
            buttons.forEach(btn => {
                html += `
                <div class="card" data-search="${btn.name} ${btn.type} ${btn.action_type} ${btn.onClick}">
                    <div class="card-header">
                        <h3 class="card-title">${escapeHtml(btn.name)}</h3>
                        <span class="card-badge ${getButtonBadgeClass(btn.type)}">${btn.type}</span>
                    </div>
                    <div class="card-content">
                        <p><span class="label">操作类型:</span> ${btn.action_type}</p>
                        <p><span class="label">处理函数:</span> <code>${escapeHtml(btn.onClick)}</code></p>
                        ${btn.text_content ? `<p><span class="label">文本内容:</span> ${escapeHtml(btn.text_content)}</p>` : ''}
                        ${btn.icon ? `<p><span class="label">图标:</span> ${escapeHtml(btn.icon)}</p>` : ''}
                        ${btn.container_type !== 'unknown' ? `<p><span class="label">容器类型:</span> ${btn.container_type}</p>` : ''}
                        <div class="file-path">${escapeHtml(btn.file_path)}:${btn.location.start_line}</div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;

            document.getElementById('button-search').addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase();
                document.querySelectorAll('#button-list .card').forEach(card => {
                    const searchText = card.dataset.search.toLowerCase();
                    card.style.display = searchText.includes(query) ? 'block' : 'none';
                });
            });
        }

        function initForms() {
            const forms = scanData.forms || [];
            const container = document.getElementById('form-list');

            if (forms.length === 0) {
                container.innerHTML = '<div class="empty-state"><h3>暂无表单数据</h3><p>扫描结果中没有检测到表单</p></div>';
                return;
            }

            let html = '';
            forms.forEach((form, idx) => {
                const fieldCount = (form.fields || []).length;
                html += `
                <div class="card" data-search="${form.name}">
                    <div class="card-header">
                        <h3 class="card-title">${escapeHtml(form.name)}</h3>
                        <span class="card-badge badge-info">${fieldCount} 个字段</span>
                    </div>
                    <div class="card-content">
                        <p><span class="label">表单实例:</span> <code>${escapeHtml(form.form_instance)}</code></p>
                        <p><span class="label">布局:</span> ${form.layout || 'vertical'}</p>
                        ${form.validation_methods && form.validation_methods.length > 0 ? 
                            `<p><span class="label">验证方法:</span> ${form.validation_methods.join(', ')}</p>` : ''}
                        ${form.submit_methods && form.submit_methods.length > 0 ? 
                            `<p><span class="label">提交方法:</span> ${form.submit_methods.join(', ')}</p>` : ''}
                        
                        <div class="file-path">${escapeHtml(form.file_path)}:${form.location.start_line}</div>

                        ${fieldCount > 0 ? `
                        <button class="toggle-btn" onclick="toggleFields(${idx})">
                            显示 ${fieldCount} 个字段详情
                        </button>
                        <div class="detail-panel" id="fields-${idx}">
                            <div style="margin-top: 15px;">
                                ${(form.fields || []).map(field => `
                                    <div style="padding: 10px; background: #f5f5f5; border-radius: 6px; margin-bottom: 8px;">
                                        <strong>${escapeHtml(field.label || field.name)}</strong>
                                        <span style="color: #999; font-size: 12px; margin-left: 10px;">
                                            ${field.type}${field.required ? ' • 必填' : ''}
                                        </span>
                                        ${field.placeholder ? `<div style="font-size: 12px; color: #666; margin-top: 4px;">
                                            ${escapeHtml(field.placeholder)}</div>` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>`;
            });
            container.innerHTML = html;

            document.getElementById('form-search').addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase();
                document.querySelectorAll('#form-list .card').forEach(card => {
                    const searchText = card.dataset.search.toLowerCase();
                    card.style.display = searchText.includes(query) ? 'block' : 'none';
                });
            });
        }

        function toggleFields(idx) {
            const panel = document.getElementById(`fields-${idx}`);
            panel.classList.toggle('expanded');
        }

        function initSteps() {
            const steps = scanData.steps || [];
            const container = document.getElementById('steps-list');

            if (steps.length === 0) {
                container.innerHTML = '<div class="empty-state"><h3>暂无步骤数据</h3><p>扫描结果中没有检测到步骤/向导</p></div>';
                return;
            }

            const stepsByWizard = {};
            steps.forEach(step => {
                const wizard = step.wizard_name || 'Unknown';
                if (!stepsByWizard[wizard]) {
                    stepsByWizard[wizard] = [];
                }
                stepsByWizard[wizard].push(step);
            });

            let html = '';
            for (const [wizard, wizardSteps] of Object.entries(stepsByWizard)) {
                const sortedSteps = [...wizardSteps].sort((a, b) => a.step_index - b.step_index);
                html += `
                <div class="chain-card">
                    <div class="chain-header">
                        <h3 class="chain-title">${escapeHtml(wizard)}</h3>
                        <span class="card-badge badge-primary">${sortedSteps.length} 个步骤</span>
                    </div>
                    <div class="chain-steps">
                        ${sortedSteps.map((step, idx) => `
                            <div class="chain-step">
                                <div class="step-icon icon-nav">${step.step_index + 1}</div>
                                <span class="step-text">${escapeHtml(step.title)}</span>
                            </div>
                            ${idx < sortedSteps.length - 1 ? '<span class="arrow">→</span>' : ''}
                        `).join('')}
                    </div>
                </div>`;
            }
            container.innerHTML = html;
        }

        function initApiCalls() {
            const apis = scanData.api_calls || [];
            const container = document.getElementById('api-list');

            if (apis.length === 0) {
                container.innerHTML = '<div class="empty-state"><h3>暂无API调用数据</h3><p>扫描结果中没有检测到API调用</p></div>';
                return;
            }

            let html = '';
            apis.forEach(api => {
                const methodClass = getMethodBadgeClass(api.method);
                html += `
                <div class="card" data-search="${api.path} ${api.method} ${api.call_type} ${api.called_from}">
                    <div class="card-header">
                        <h3 class="card-title"><code>${escapeHtml(api.path)}</code></h3>
                        <span class="card-badge ${methodClass}">${api.method}</span>
                    </div>
                    <div class="card-content">
                        <p><span class="label">调用类型:</span> ${api.call_type}</p>
                        ${api.called_from ? `<p><span class="label">调用位置:</span> <code>${escapeHtml(api.called_from)}</code></p>` : ''}
                        <div class="file-path">${escapeHtml(api.file_path)}:${api.location.start_line}</div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;

            document.getElementById('api-search').addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase();
                document.querySelectorAll('#api-list .card').forEach(card => {
                    const searchText = card.dataset.search.toLowerCase();
                    card.style.display = searchText.includes(query) ? 'block' : 'none';
                });
            });
        }

        function initChains() {
            const chains = scanData.operation_chains || [];
            const container = document.getElementById('chains-list');

            if (chains.length === 0) {
                container.innerHTML = '<div class="empty-state"><h3>暂无操作链数据</h3><p>扫描结果中没有检测到操作链</p></div>';
                return;
            }

            let html = '';
            chains.forEach(chain => {
                html += renderChainCard(chain, true);
            });
            container.innerHTML = html;
        }

        function renderChainCard(chain, showDetails = false) {
            const metadata = chain.metadata || {};
            return `
            <div class="chain-card">
                <div class="chain-header">
                    <h3 class="chain-title">${escapeHtml(chain.name)}</h3>
                    <div style="display: flex; gap: 10px;">
                        ${metadata.button_clicks ? `<span class="card-badge badge-primary">${metadata.button_clicks} 次点击</span>` : ''}
                        ${metadata.form_fills ? `<span class="card-badge badge-success">${metadata.form_fills} 个表单</span>` : ''}
                        ${metadata.api_calls ? `<span class="card-badge badge-warning">${metadata.api_calls} 次API</span>` : ''}
                    </div>
                </div>
                ${chain.component_name ? `<div class="file-path" style="margin-bottom: 15px;">
                    组件: ${escapeHtml(chain.component_name)} | ${escapeHtml(chain.file_path)}
                </div>` : ''}
                <div class="chain-steps">
                    ${chain.steps.map((step, idx) => `
                        <div class="chain-step">
                            <div class="step-icon ${getStepIconClass(step.type)}">
                                ${getStepIcon(step.type)}
                            </div>
                            <span class="step-text">${escapeHtml(step.description || step.type)}</span>
                        </div>
                        ${idx < chain.steps.length - 1 ? '<span class="arrow">→</span>' : ''}
                    `).join('')}
                </div>
            </div>`;
        }

        function initGraph() {
            const cy = cytoscape({
                container: document.getElementById('cy'),
                style: [
                    {
                        selector: 'node',
                        style: {
                            'background-color': function(ele) {
                                const type = ele.data('nodeType');
                                if (type === 'button') return '#667eea';
                                if (type === 'form') return '#2193b0';
                                if (type === 'api') return '#f093fb';
                                if (type === 'step') return '#11998e';
                                if (type === 'chain') return '#f5af19';
                                return '#999';
                            },
                            'label': 'data(label)',
                            'color': '#fff',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'font-size': '12px',
                            'width': function(ele) {
                                const type = ele.data('nodeType');
                                if (type === 'chain') return '80px';
                                return '60px';
                            },
                            'height': function(ele) {
                                const type = ele.data('nodeType');
                                if (type === 'chain') return '80px';
                                return '60px';
                            },
                            'shape': 'ellipse',
                            'border-width': 2,
                            'border-color': '#fff',
                            'text-wrap': 'wrap',
                            'text-max-width': '60px'
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 2,
                            'line-color': '#ccc',
                            'target-arrow-color': '#999',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'label': 'data(label)',
                            'font-size': '10px',
                            'color': '#666'
                        }
                    },
                    {
                        selector: ':selected',
                        style: {
                            'background-color': '#ff4081',
                            'line-color': '#ff4081',
                            'target-arrow-color': '#ff4081',
                            'source-arrow-color': '#ff4081'
                        }
                    }
                ],
                elements: buildGraphElements(),
                layout: {
                    name: 'breadthfirst',
                    directed: true,
                    padding: 30,
                    spacingFactor: 1.5
                }
            });

            cy.on('tap', 'node', function(evt) {
                const node = evt.target;
                console.log('选中节点:', node.id(), node.data());
            });
        }

        function buildGraphElements() {
            const elements = [];
            const addedNodes = new Set();

            scanData.operation_chains.forEach(chain => {
                const chainId = `chain_${chain.id}`;
                if (!addedNodes.has(chainId)) {
                    elements.push({
                        data: {
                            id: chainId,
                            label: chain.name,
                            nodeType: 'chain'
                        }
                    });
                    addedNodes.add(chainId);
                }

                chain.steps.forEach((step, idx) => {
                    const stepId = `step_${chain.id}_${idx}`;
                    let nodeType = 'step';
                    let label = step.description || step.type;

                    if (step.type === 'button_click') {
                        nodeType = 'button';
                        if (step.button && step.button.name) {
                            label = step.button.name;
                        }
                    } else if (step.type === 'form_fill' || step.type === 'form_validate') {
                        nodeType = 'form';
                        if (step.form && step.form.name) {
                            label = step.form.name;
                        }
                    } else if (step.type === 'api_call') {
                        nodeType = 'api';
                        if (step.api_call) {
                            label = `${step.api_call.method || 'API'} ${step.api_call.path || ''}`;
                        }
                    }

                    if (!addedNodes.has(stepId)) {
                        elements.push({
                            data: {
                                id: stepId,
                                label: label.substring(0, 20),
                                nodeType: nodeType
                            }
                        });
                        addedNodes.add(stepId);
                    }

                    if (idx === 0) {
                        elements.push({
                            data: {
                                id: `edge_chain_${chainId}_${stepId}`,
                                source: chainId,
                                target: stepId,
                                label: '开始'
                            }
                        });
                    } else {
                        const prevStepId = `step_${chain.id}_${idx - 1}`;
                        elements.push({
                            data: {
                                id: `edge_${prevStepId}_${stepId}`,
                                source: prevStepId,
                                target: stepId,
                                label: '→'
                            }
                        });
                    }
                });
            });

            return elements;
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function getButtonBadgeClass(type) {
            if (type === 'primary') return 'badge-primary';
            if (type === 'danger') return 'badge-danger';
            if (type === 'link') return 'badge-info';
            return 'badge-success';
        }

        function getMethodBadgeClass(method) {
            if (!method) return 'badge-primary';
            const m = method.toUpperCase();
            if (m === 'GET') return 'badge-success';
            if (m === 'POST') return 'badge-primary';
            if (m === 'PUT') return 'badge-warning';
            if (m === 'DELETE') return 'badge-danger';
            if (m === 'PATCH') return 'badge-info';
            return 'badge-primary';
        }

        function getStepIconClass(type) {
            if (type === 'button_click') return 'icon-click';
            if (type === 'form_fill' || type === 'form_validate') return 'icon-form';
            if (type === 'api_call') return 'icon-api';
            if (type === 'step_navigate') return 'icon-nav';
            if (type === 'modal_open' || type === 'modal_close') return 'icon-modal';
            return 'icon-nav';
        }

        function getStepIcon(type) {
            if (type === 'button_click') return '🖱️';
            if (type === 'form_fill' || type === 'form_validate') return '📝';
            if (type === 'api_call') return '🌐';
            if (type === 'step_navigate') return '→';
            if (type === 'modal_open') return '📂';
            if (type === 'modal_close') return '📁';
            return '⚡';
        }
    </script>
</body>
</html>
'''
