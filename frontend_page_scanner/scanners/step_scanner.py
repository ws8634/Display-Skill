#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤/向导扫描器
用于识别 TSX 文件中的 Ant Design Steps 组件和向导模式
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    StepInfo, Location
)


class StepScanner:
    """步骤/向导扫描器"""

    def __init__(self):
        self.step_counter = 0

    def scan_file(self, file_path: str, content: str) -> List[StepInfo]:
        """扫描单个文件中的步骤/向导"""
        steps = []

        steps_definitions = self._find_steps_definitions(content)

        for idx, step_def in enumerate(steps_definitions):
            step_info = self._extract_step_info(file_path, content, step_def, idx)
            if step_info:
                steps.append(step_info)
                self.step_counter += 1

        wizard_components = self._find_wizard_components(content)
        for wizard in wizard_components:
            wizard_steps = self._extract_wizard_steps(file_path, content, wizard)
            for step in wizard_steps:
                exists = any(s.step_index == step.step_index and s.wizard_name == step.wizard_name for s in steps)
                if not exists:
                    steps.append(step)
                    self.step_counter += 1

        return steps

    def _find_steps_definitions(self, content: str) -> List[Dict[str, Any]]:
        """查找步骤数组定义"""
        definitions = []

        pattern = re.compile(r'const\s+(\w+)\s*=\s*\[([^\]]+)\]')
        for match in pattern.finditer(content):
            var_name = match.group(1)
            array_content = match.group(2)

            if re.search(r'["\'].*步骤.*["\']', array_content) or \
               re.search(r'["\'].*下一步.*["\']', array_content) or \
               re.search(r'["\'].*选择.*["\']', array_content) or \
               re.search(r'["\'].*配置.*["\']', array_content) or \
               re.search(r'["\'].*测试.*["\']', array_content) or \
               re.search(r'["\'].*基本.*["\']', array_content) or \
               re.search(r'["\'].*信息.*["\']', array_content) or \
               re.search(r'["\'].*存储.*["\']', array_content) or \
               re.search(r'["\'].*网络.*["\']', array_content) or \
               re.search(r'["\'].*登录.*["\']', array_content) or \
               re.search(r'["\'].*高级.*["\']', array_content):

                step_titles = self._parse_step_titles(array_content)
                if step_titles:
                    definitions.append({
                        'var_name': var_name,
                        'step_titles': step_titles,
                        'start_pos': match.start(),
                        'start_line': content[:match.start()].count('\n') + 1
                    })

        return definitions

    def _parse_step_titles(self, array_content: str) -> List[str]:
        """解析步骤标题"""
        titles = []

        pattern = re.compile(r'["\']([^"\']+步骤[^"\']*)["\']')
        for match in pattern.finditer(array_content):
            titles.append(match.group(1))

        if not titles:
            pattern2 = re.compile(r'["\']([^"\']+)["\']')
            for match in pattern2.finditer(array_content):
                title = match.group(1)
                if len(title) <= 15 and len(title) >= 2:
                    if any(keyword in title for keyword in ['选择', '配置', '测试', '基本', '信息', '存储', '网络', '登录', '高级', '计算', '连接', '凭据', '设置']):
                        titles.append(title)

        return titles

    def _extract_step_info(self, file_path: str, content: str, step_def: Dict[str, Any], idx: int) -> Optional[StepInfo]:
        """提取步骤信息"""
        var_name = step_def['var_name']
        step_titles = step_def['step_titles']

        if not step_titles:
            return None

        steps = []
        for step_idx, title in enumerate(step_titles):
            step_id = self._generate_id(file_path, var_name, step_idx)

            step = StepInfo(
                id=step_id,
                wizard_name=var_name,
                step_index=step_idx,
                title=title,
                file_path=file_path,
                location=Location(
                    start_line=step_def['start_line'],
                    end_line=step_def['start_line']
                ),
                next_step=step_idx + 1 if step_idx < len(step_titles) - 1 else None,
                prev_step=step_idx - 1 if step_idx > 0 else None,
                buttons_in_step=self._find_buttons_for_step(content, step_idx),
                form_fields_in_step=[],
                description=f"步骤 {step_idx + 1}: {title}",
                metadata={}
            )

            steps.append(step)

        return steps[0] if steps else None

    def _find_wizard_components(self, content: str) -> List[Dict[str, Any]]:
        """查找向导组件"""
        wizards = []

        pattern = re.compile(r'<Steps[^>]*>', re.MULTILINE)
        for match in pattern.finditer(content):
            start_pos = match.start()
            full_tag = match.group(0)
            start_line = content[:start_pos].count('\n') + 1

            wizard = {
                'start_pos': start_pos,
                'full_tag': full_tag,
                'start_line': start_line,
                'step_titles': []
            }

            current_match = re.search(r'current\s*=\s*\{([^}]+)\}', full_tag)
            if current_match:
                wizard['current_var'] = current_match.group(1)

            wizards.append(wizard)

        return wizards

    def _extract_wizard_steps(self, file_path: str, content: str, wizard: Dict[str, Any]) -> List[StepInfo]:
        """从向导组件提取步骤"""
        steps = []

        step_titles = []
        start_pos = wizard['start_pos']

        step_pattern = re.compile(r'<Step[^>]*title\s*=\s*\{?\s*["\']([^"\']+)["\']')
        for match in step_pattern.finditer(content, start_pos, start_pos + 3000):
            step_titles.append(match.group(1))

        if not step_titles:
            step_pattern2 = re.compile(r'title\s*=\s*["\']([^"\']+步骤[^"\']*)["\']')
            for match in step_pattern2.finditer(content, start_pos, start_pos + 3000):
                step_titles.append(match.group(1))

        for step_idx, title in enumerate(step_titles):
            step_id = self._generate_id(file_path, 'StepsComponent', step_idx)

            step = StepInfo(
                id=step_id,
                wizard_name='StepsComponent',
                step_index=step_idx,
                title=title,
                file_path=file_path,
                location=Location(
                    start_line=wizard['start_line'],
                    end_line=wizard['start_line']
                ),
                next_step=step_idx + 1 if step_idx < len(step_titles) - 1 else None,
                prev_step=step_idx - 1 if step_idx > 0 else None,
                buttons_in_step=self._find_buttons_for_step(content, step_idx),
                form_fields_in_step=[],
                description=f"步骤 {step_idx + 1}: {title}",
                metadata={}
            )

            steps.append(step)

        return steps

    def _find_buttons_for_step(self, content: str, step_idx: int) -> List[str]:
        """查找步骤相关的按钮处理函数"""
        buttons = []

        if step_idx == 0:
            pattern = re.compile(r'(handle[A-Z][a-zA-Z]*Select)')
            for match in pattern.finditer(content):
                func_name = match.group(1)
                if func_name not in buttons:
                    buttons.append(func_name)
        else:
            if 'handleNext' in content:
                buttons.append('handleNext')
            if 'handlePrev' in content:
                buttons.append('handlePrev')
            if 'next' in content:
                buttons.append('next')
            if 'prev' in content:
                buttons.append('prev')

        return buttons

    def _generate_id(self, file_path: str, wizard_name: str, step_index: int) -> str:
        """生成唯一ID"""
        key = f"{file_path}#{wizard_name}#{step_index}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
