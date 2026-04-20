#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版步骤/向导扫描器
支持数组定义步骤、Steps组件、步骤切换函数等各种模式
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    StepInfo, Location
)


class StepScanner:
    """增强版步骤/向导扫描器"""

    STEP_KEYWORDS = [
        '步骤', '选择', '配置', '测试', '基本', '信息', '存储', '网络',
        '登录', '高级', '计算', '连接', '凭据', '设置', '下一步',
        '上一步', '步骤0', '步骤1', 'step', 'Step', 'STEP',
        '向导', 'wizard', 'Wizard', 'WIZARD',
        '确认', 'review', 'Review', 'REVIEW',
        '完成', 'finish', 'Finish', 'FINISH',
    ]

    def __init__(self):
        self.step_counter = 0

    def scan_file(self, file_path: str, content: str) -> List[StepInfo]:
        """扫描单个文件中的步骤/向导"""
        steps = []

        array_steps = self._find_array_step_definitions(content)
        for wizard_name, step_defs in array_steps.items():
            for idx, step_def in enumerate(step_defs):
                step_info = self._create_step_info(
                    file_path, content, wizard_name, idx, step_def['title'], step_def['start_line']
                )
                if step_info:
                    steps.append(step_info)
                    self.step_counter += 1

        steps_component = self._find_steps_component(content)
        for wizard_name, step_defs in steps_component.items():
            for idx, step_def in enumerate(step_defs):
                exists = any(
                    s.step_index == idx and s.wizard_name == wizard_name for s in steps
                )
                if not exists:
                    step_info = self._create_step_info(
                        file_path, content, wizard_name, idx, step_def['title'], step_def['start_line']
                    )
                    if step_info:
                        steps.append(step_info)
                        self.step_counter += 1

        wizard_patterns = self._find_wizard_patterns(content)
        for wizard_name, wizard_info in wizard_patterns.items():
            step_count = wizard_info.get('step_count', 0)
            for idx in range(step_count):
                exists = any(
                    s.step_index == idx and s.wizard_name == wizard_name for s in steps
                )
                if not exists:
                    step_info = self._create_step_info(
                        file_path, content, wizard_name, idx, 
                        f"步骤 {idx + 1}", wizard_info['start_line']
                    )
                    if step_info:
                        steps.append(step_info)
                        self.step_counter += 1

        return steps

    def _find_array_step_definitions(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """查找数组形式的步骤定义"""
        wizard_steps = {}

        patterns = [
            r'(?:const|let|var)\s+(\w*[Ss]tep\w*|\w*[Ss]tep\w*|steps|Steps|STEPS)\s*=\s*\[',
            r'(?:const|let|var)\s+(\w*[Ww]izard\w*|\w*[Ww]izard\w*)\s*=\s*\[',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                var_name = match.group(1)
                start_pos = match.start()
                start_line = content[:start_pos].count('\n') + 1

                close_pos = self._find_matching_bracket(content, match.end(), '[', ']')

                if close_pos > match.end():
                    array_content = content[match.end():close_pos]
                    step_defs = self._parse_array_steps(array_content, start_line)

                    if step_defs:
                        if var_name not in wizard_steps:
                            wizard_steps[var_name] = []
                        for idx, step_title in enumerate(step_defs):
                            wizard_steps[var_name].append({
                                'title': step_title,
                                'start_line': start_line
                            })

        return wizard_steps

    def _find_matching_bracket(self, content: str, start_pos: int, 
                                  open_char: str, close_char: str) -> int:
        """查找匹配的括号"""
        depth = 1
        pos = start_pos

        while pos < len(content):
            ch = content[pos]

            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return pos + 1

            pos += 1

        return len(content)

    def _parse_array_steps(self, array_content: str, start_line: int) -> List[str]:
        """解析数组中的步骤标题"""
        steps = []

        string_pattern = re.compile(r'["\']([^"\']*步骤[^"\']*)["\']')
        for match in string_pattern.finditer(array_content):
            title = match.group(1)
            if title and title not in steps:
                steps.append(title)

        if not steps:
            object_pattern = re.compile(
                r'\{\s*title\s*:\s*["\']([^"\']+)["\']',
                re.MULTILINE
            )
            for match in object_pattern.finditer(array_content):
                title = match.group(1)
                if title and title not in steps:
                    steps.append(title)

        if not steps:
            simple_string_pattern = re.compile(r'["\']([^"\']{2,20})["\']')
            for match in simple_string_pattern.finditer(array_content):
                title = match.group(1)

                is_step_title = False
                if len(title) >= 2 and len(title) <= 20:
                    for keyword in self.STEP_KEYWORDS:
                        if keyword in title:
                            is_step_title = True
                            break

                    if re.search(r'[步骤一二三四五六七八九十1234567890]+', title):
                        is_step_title = True

                if is_step_title and title not in steps:
                    steps.append(title)

        return steps

    def _find_steps_component(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """查找 Ant Design Steps 组件"""
        wizard_steps = {}

        steps_tag_pattern = re.compile(r'<Steps[^>]*>', re.DOTALL)
        for match in steps_tag_pattern.finditer(content):
            start_pos = match.start()
            start_line = content[:start_pos].count('\n') + 1

            step_title_pattern = re.compile(r'<Step[^>]*title\s*=\s*["\']([^"\']+)["\']')
            step_titles = []
            for step_match in step_title_pattern.finditer(content, start_pos, start_pos + 3000):
                step_titles.append({
                    'title': step_match.group(1),
                    'start_line': start_line
                })

            if step_titles:
                wizard_name = f"StepsComponent_{self.step_counter}"
                wizard_steps[wizard_name] = step_titles

        return wizard_steps

    def _find_wizard_patterns(self, content: str) -> Dict[str, Dict[str, Any]]:
        """查找向导模式（通过 step 变量和切换函数）"""
        wizards = {}

        step_state_patterns = [
            r'(?:const|let|var)\s*\[?\s*(\w*[Ss]tep\w*|\w*[Ss]tep\w*|currentStep|currentStepIndex|step|Step)\s*,\s*\w+\s*\]?\s*=\s*useState',
        ]

        for pattern in step_state_patterns:
            for match in re.finditer(pattern, content):
                var_name = match.group(1)
                start_pos = match.start()
                start_line = content[:start_pos].count('\n') + 1

                has_next = bool(re.search(r'handleNext|nextStep|next\s*=\s*\(', content[max(0, start_pos - 500):start_pos + 2000]))
                has_prev = bool(re.search(r'handlePrev|prevStep|previous\s*=\s*\(', content[max(0, start_pos - 500):start_pos + 2000]))

                if has_next or has_prev:
                    wizard_name = f"Wizard_{var_name}"

                    step_count = 3

                    step_count_match = re.search(r'const\s+steps\s*=\s*\[([^\]]+)\]', content)
                    if step_count_match:
                        step_text = step_count_match.group(1)
                        step_count = step_text.count(',') + 1

                    wizards[wizard_name] = {
                        'start_line': start_line,
                        'step_count': step_count,
                        'step_var': var_name,
                        'has_next': has_next,
                        'has_prev': has_prev
                    }

        return wizards

    def _create_step_info(self, file_path: str, content: str, 
                           wizard_name: str, step_index: int, 
                           title: str, start_line: int) -> Optional[StepInfo]:
        """创建步骤信息"""
        step_id = self._generate_id(file_path, wizard_name, step_index)

        buttons_in_step = self._find_buttons_for_step(content, step_index, start_line)
        form_fields_in_step = self._find_form_fields_for_step(content, step_index, start_line)

        step = StepInfo(
            id=step_id,
            wizard_name=wizard_name,
            step_index=step_index,
            title=title,
            file_path=file_path,
            location=Location(
                start_line=start_line,
                end_line=start_line
            ),
            next_step=step_index + 1,
            prev_step=step_index - 1 if step_index > 0 else None,
            buttons_in_step=buttons_in_step,
            form_fields_in_step=form_fields_in_step,
            description=f"步骤 {step_index + 1}: {title}",
            metadata={}
        )

        return step

    def _find_buttons_for_step(self, content: str, step_index: int, start_line: int) -> List[str]:
        """查找步骤相关的按钮处理函数"""
        buttons = []

        if step_index == 0:
            provider_pattern = re.compile(r'(handle[A-Z][a-zA-Z]*Select)', re.MULTILINE)
            for match in provider_pattern.finditer(content):
                func_name = match.group(1)
                if func_name not in buttons:
                    buttons.append(func_name)
        else:
            next_pattern = re.compile(r'(handleNext|nextStep|next\s*=\s*\([^)]*\)\s*=>)', re.MULTILINE)
            for match in next_pattern.finditer(content):
                buttons.append('handleNext')
                break

            prev_pattern = re.compile(r'(handlePrev|prevStep|previous\s*=\s*\([^)]*\)\s*=>)', re.MULTILINE)
            for match in prev_pattern.finditer(content):
                buttons.append('handlePrev')
                break

        submit_pattern = re.compile(r'(handleSubmit|handleFinish|handleOk)', re.MULTILINE)
        for match in submit_pattern.finditer(content):
            buttons.append(match.group(1))
            break

        return buttons

    def _find_form_fields_for_step(self, content: str, step_index: int, start_line: int) -> List[str]:
        """查找步骤相关的表单字段"""
        fields = []

        form_item_pattern = re.compile(r'<Form\.Item[^>]*name\s*=\s*["\'](\w+)["\']')
        for match in form_item_pattern.finditer(content):
            field_name = match.group(1)
            if field_name not in fields:
                fields.append(field_name)

        return fields

    def _generate_id(self, file_path: str, wizard_name: str, step_index: int) -> str:
        """生成唯一ID"""
        key = f"{file_path}#{wizard_name}#{step_index}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
