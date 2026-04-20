#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版表单扫描器
支持 Form.useForm、Form.Item、Form.List、动态渲染等各种模式
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    FormInfo, FormFieldInfo, FormFieldType, Location
)


class FormScanner:
    """增强版表单扫描器"""

    FIELD_TYPE_PATTERNS = {
        r'<Input\b': FormFieldType.INPUT,
        r'<Input\.Password\b': FormFieldType.PASSWORD,
        r'<Input\.TextArea\b': FormFieldType.TEXTAREA,
        r'<TextArea\b': FormFieldType.TEXTAREA,
        r'<Select\b': FormFieldType.SELECT,
        r'<Cascader\b': FormFieldType.CASCADER,
        r'<Switch\b': FormFieldType.SWITCH,
        r'<Radio\b': FormFieldType.RADIO,
        r'<Checkbox\b': FormFieldType.CHECKBOX,
        r'<DatePicker\b': FormFieldType.DATE_PICKER,
        r'<RangePicker\b': FormFieldType.RANGE_PICKER,
        r'<Upload\b': FormFieldType.UPLOAD,
        r'<InputNumber\b': FormFieldType.INPUT_NUMBER,
    }

    def __init__(self):
        self.form_counter = 0

    def scan_file(self, file_path: str, content: str) -> List[FormInfo]:
        """扫描单个文件中的表单"""
        forms = []

        form_instances = self._find_form_instances(content)

        for instance_name, instance_info in form_instances.items():
            form_components = self._find_form_components(content, instance_name)

            for form_info in form_components:
                form_id = self._generate_id(file_path, form_info['start_line'], instance_name)

                fields = self._extract_form_fields(content, form_info, instance_name)

                validation_methods = self._find_validation_methods(content, instance_name)
                submit_methods = self._find_submit_methods(content, instance_name)

                layout = form_info.get('layout', 'vertical')

                form = FormInfo(
                    id=form_id,
                    name=self._generate_name(instance_name, form_info, file_path),
                    form_instance=instance_name,
                    file_path=file_path,
                    location=Location(
                        start_line=form_info['start_line'],
                        end_line=form_info['end_line']
                    ),
                    fields=fields,
                    validation_methods=validation_methods,
                    submit_methods=submit_methods,
                    layout=layout,
                    metadata={
                        'form_definition': form_info.get('definition', ''),
                        'has_form_list': form_info.get('has_form_list', False)
                    }
                )

                forms.append(form)
                self.form_counter += 1

        if not forms:
            simple_forms = self._find_simple_forms(content, file_path)
            forms.extend(simple_forms)

        return forms

    def _find_form_instances(self, content: str) -> Dict[str, Dict[str, Any]]:
        """查找所有 Form.useForm() 实例"""
        instances = {}

        patterns = [
            r'(?:const|let|var)\s*\[?\s*(\w+)\s*,\s*\w*\s*\]?\s*=\s*Form\.useForm\s*\(',
            r'(?:const|let|var)\s*\[?\s*(\w+)\s*,\s*\w*\s*\]?\s*=\s*useForm\s*\(',
            r'(?:const|let|var)\s*(\w+)\s*=\s*Form\.useForm\s*\(',
            r'(?:const|let|var)\s*(\w+)\s*=\s*useForm\s*\(',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                var_name = match.group(1)
                start_line = content[:match.start()].count('\n') + 1

                if var_name not in instances:
                    instances[var_name] = {
                        'name': var_name,
                        'start_line': start_line,
                        'start_pos': match.start()
                    }

        return instances

    def _find_form_components(self, content: str, instance_name: str) -> List[Dict[str, Any]]:
        """查找 Form 组件"""
        forms = []

        pattern = r'<Form\b[^>]*form\s*=\s*\{?\s*' + instance_name + r'\s*\}?[^>]*>'
        form_pattern = re.compile(pattern, re.DOTALL)

        for match in form_pattern.finditer(content):
            open_tag = match.group(0)
            start_pos = match.start()
            start_line = content[:start_pos].count('\n') + 1

            close_pos = self._find_matching_closing_tag(content, match.end(), 'Form')

            layout_match = re.search(r'layout\s*=\s*["\'](\w+)["\']', open_tag)
            layout = layout_match.group(1) if layout_match else 'vertical'

            has_form_list = bool(re.search(r'Form\.List|form\.List', content[start_pos:close_pos]))

            forms.append({
                'start_pos': start_pos,
                'end_pos': close_pos,
                'start_line': start_line,
                'end_line': content[:close_pos].count('\n') + 1,
                'definition': open_tag[:200] if len(open_tag) > 200 else open_tag,
                'layout': layout,
                'has_form_list': has_form_list
            })

        return forms

    def _find_matching_closing_tag(self, content: str, start_pos: int, tag_name: str) -> int:
        """查找匹配的闭合标签，处理嵌套情况"""
        depth = 1
        pos = start_pos

        open_pattern = re.compile(rf'<{tag_name}\b')
        close_pattern = re.compile(rf'</{tag_name}\s*>')

        while pos < len(content):
            open_match = open_pattern.search(content, pos)
            close_match = close_pattern.search(content, pos)

            if not close_match:
                return pos

            if open_match and open_match.start() < close_match.start():
                depth += 1
                pos = open_match.end()
            else:
                depth -= 1
                if depth == 0:
                    return close_match.end()
                pos = close_match.end()

        return len(content)

    def _extract_form_fields(self, content: str, form_info: Dict[str, Any], 
                               instance_name: str) -> List[FormFieldInfo]:
        """提取表单字段"""
        fields = []
        seen_names = set()

        form_content = content[form_info['start_pos']:form_info['end_pos']]

        form_item_pattern = re.compile(
            r'<Form\.Item[^>]*name\s*=\s*["\'](\w+)["\'][^>]*>',
            re.DOTALL
        )

        form_item_pattern2 = re.compile(
            r'<Form\.Item[^>]*name\s*=\s*\{([^}]+)\}[^>]*>',
            re.DOTALL
        )

        form_item_pattern3 = re.compile(
            r'<Form\.Item[^>]*label\s*=\s*["\']([^"\']+)["\'][^>]*>',
            re.DOTALL
        )

        for match in form_item_pattern.finditer(form_content):
            field_name = match.group(1)
            if field_name in seen_names:
                continue
            seen_names.add(field_name)

            full_match = match.group(0)
            relative_start = match.start()
            absolute_start = form_info['start_pos'] + relative_start
            start_line = content[:absolute_start].count('\n') + 1

            label_match = re.search(r'label\s*=\s*["\']([^"\']+)["\']', full_match)
            label = label_match.group(1) if label_match else field_name

            required_match = re.search(r'required\s*=\s*\{(true|True)\}', full_match)
            is_required = bool(required_match)

            rules_match = re.search(r'rules\s*=\s*\{([^}]+)\}', full_match)
            rules = []
            if rules_match:
                rules_text = rules_match.group(1)
                if 'required' in rules_text.lower() or '必填' in rules_text:
                    is_required = True

            field_type = self._detect_field_type(form_content, relative_start, field_name)

            placeholder_match = re.search(r'placeholder\s*=\s*["\']([^"\']+)["\']', form_content[relative_start:relative_start + 500])
            placeholder = placeholder_match.group(1) if placeholder_match else ''

            field = FormFieldInfo(
                name=field_name,
                label=label,
                type=field_type,
                required=is_required,
                rules=rules,
                location=Location(
                    start_line=start_line,
                    end_line=start_line
                ),
                placeholder=placeholder,
                metadata={
                    'form_item_tag': full_match[:200] if len(full_match) > 200 else full_match
                }
            )
            fields.append(field)

        for match in form_item_pattern3.finditer(form_content):
            label = match.group(1)
            full_match = match.group(0)

            name_match = re.search(r'name\s*=\s*["\'](\w+)["\']', full_match)
            if name_match:
                field_name = name_match.group(1)
            else:
                name_match2 = re.search(r'name\s*=\s*\{([^}]+)\}', full_match)
                if name_match2:
                    field_name = name_match2.group(1)
                else:
                    field_name = f"field_{len(fields)}"

            if field_name in seen_names:
                continue
            seen_names.add(field_name)

            relative_start = match.start()
            absolute_start = form_info['start_pos'] + relative_start
            start_line = content[:absolute_start].count('\n') + 1

            required_match = re.search(r'required\s*=\s*\{(true|True)\}', full_match)
            is_required = bool(required_match)

            field_type = self._detect_field_type(form_content, relative_start, field_name)

            placeholder_match = re.search(r'placeholder\s*=\s*["\']([^"\']+)["\']', form_content[relative_start:relative_start + 500])
            placeholder = placeholder_match.group(1) if placeholder_match else ''

            field = FormFieldInfo(
                name=field_name,
                label=label,
                type=field_type,
                required=is_required,
                rules=[],
                location=Location(
                    start_line=start_line,
                    end_line=start_line
                ),
                placeholder=placeholder,
                metadata={
                    'form_item_tag': full_match[:200] if len(full_match) > 200 else full_match
                }
            )
            fields.append(field)

        return fields

    def _detect_field_type(self, form_content: str, relative_start: int, field_name: str) -> FormFieldType:
        """检测字段类型"""
        search_start = max(0, relative_start - 20)
        search_end = min(len(form_content), relative_start + 800)
        search_area = form_content[search_start:search_end]

        for pattern, field_type in self.FIELD_TYPE_PATTERNS.items():
            if re.search(pattern, search_area):
                return field_type

        if 'Password' in search_area or 'password' in field_name.lower():
            return FormFieldType.PASSWORD
        elif 'Select' in search_area or 'select' in field_name.lower():
            return FormFieldType.SELECT
        elif 'TextArea' in search_area or 'textarea' in field_name.lower():
            return FormFieldType.TEXTAREA
        elif 'Switch' in search_area or 'switch' in field_name.lower():
            return FormFieldType.SWITCH
        elif 'Radio' in search_area:
            return FormFieldType.RADIO
        elif 'Checkbox' in search_area:
            return FormFieldType.CHECKBOX
        elif 'DatePicker' in search_area:
            return FormFieldType.DATE_PICKER
        elif 'Upload' in search_area:
            return FormFieldType.UPLOAD
        elif 'InputNumber' in search_area:
            return FormFieldType.INPUT_NUMBER
        elif 'Input' in search_area:
            return FormFieldType.INPUT

        return FormFieldType.INPUT

    def _find_validation_methods(self, content: str, instance_name: str) -> List[str]:
        """查找表单验证方法"""
        methods = []

        validate_patterns = [
            rf'{instance_name}\.validateFields',
            rf'{instance_name}\.validate',
            rf'{instance_name}\.getFieldsValue',
            rf'{instance_name}\.setFieldsValue',
            rf'{instance_name}\.resetFields',
        ]

        for pattern in validate_patterns:
            for match in re.finditer(pattern, content):
                method = match.group(0)
                if method not in methods:
                    methods.append(method)

        return methods

    def _find_submit_methods(self, content: str, instance_name: str) -> List[str]:
        """查找表单提交方法"""
        methods = []

        submit_patterns = [
            r'(?:const|let|var|async\s+function|function)\s*(\w+Submit|handleOk|handleFinish|onSubmit|onFinish)\s*[=:(]',
            r'(?:const|let|var)\s*(\w+Submit|handleOk|handleFinish|onSubmit|onFinish)\s*=\s*async',
        ]

        for pattern in submit_patterns:
            for match in re.finditer(pattern, content):
                method = match.group(1)
                if method not in methods:
                    methods.append(method)

        return methods

    def _find_simple_forms(self, content: str, file_path: str) -> List[FormInfo]:
        """查找简单表单（没有 Form.useForm 实例的情况）"""
        forms = []

        simple_form_pattern = re.compile(r'<Form\b[^>]*>', re.DOTALL)

        for match in simple_form_pattern.finditer(content):
            open_tag = match.group(0)

            if 'form={' in open_tag or 'form=' in open_tag:
                continue

            start_pos = match.start()
            start_line = content[:start_pos].count('\n') + 1

            close_pos = self._find_matching_closing_tag(content, match.end(), 'Form')

            form_content = content[start_pos:close_pos]

            form_items = list(re.finditer(r'<Form\.Item[^>]*>', form_content))
            if len(form_items) < 1:
                continue

            form_id = self._generate_id(file_path, start_line, 'simple_form')

            layout_match = re.search(r'layout\s*=\s*["\'](\w+)["\']', open_tag)
            layout = layout_match.group(1) if layout_match else 'vertical'

            fields = []
            seen_names = set()

            for item_match in re.finditer(r'<Form\.Item[^>]*>', form_content):
                item_tag = item_match.group(0)
                relative_start = item_match.start()

                name_match = re.search(r'name\s*=\s*["\'](\w+)["\']', item_tag)
                if not name_match:
                    name_match = re.search(r'name\s*=\s*\{([^}]+)\}', item_tag)
                    if not name_match:
                        continue

                field_name = name_match.group(1)
                if field_name in seen_names:
                    continue
                seen_names.add(field_name)

                label_match = re.search(r'label\s*=\s*["\']([^"\']+)["\']', item_tag)
                label = label_match.group(1) if label_match else field_name

                required_match = re.search(r'required\s*=\s*\{(true|True)\}', item_tag)
                is_required = bool(required_match)

                field_type = self._detect_field_type(form_content, relative_start, field_name)

                absolute_start = start_pos + relative_start
                start_line_item = content[:absolute_start].count('\n') + 1

                field = FormFieldInfo(
                    name=field_name,
                    label=label,
                    type=field_type,
                    required=is_required,
                    rules=[],
                    location=Location(
                        start_line=start_line_item,
                        end_line=start_line_item
                    ),
                    placeholder='',
                    metadata={}
                )
                fields.append(field)

            if fields:
                form = FormInfo(
                    id=form_id,
                    name=f"simple_form_{start_line}",
                    form_instance="",
                    file_path=file_path,
                    location=Location(
                        start_line=start_line,
                        end_line=content[:close_pos].count('\n') + 1
                    ),
                    fields=fields,
                    validation_methods=[],
                    submit_methods=[],
                    layout=layout,
                    metadata={
                        'is_simple_form': True,
                        'form_tag': open_tag[:200] if len(open_tag) > 200 else open_tag
                    }
                )
                forms.append(form)
                self.form_counter += 1

        return forms

    def _generate_id(self, file_path: str, line: int, instance_name: str) -> str:
        """生成唯一ID"""
        key = f"{file_path}#{line}#{instance_name}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def _generate_name(self, instance_name: str, form_info: Dict[str, Any], file_path: str) -> str:
        """生成表单名称"""
        file_name = Path(file_path).stem

        if form_info.get('has_form_list', False):
            return f"{file_name}_form_with_list"

        if instance_name:
            return f"{file_name}_{instance_name}_form"

        return f"{file_name}_form"
