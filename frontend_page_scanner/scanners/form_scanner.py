#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表单扫描器
用于识别 TSX 文件中的 Ant Design Form 组件及其字段
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    FormInfo, FormFieldInfo, FormFieldType, Location
)


class FormScanner:
    """表单扫描器"""

    FORM_FIELD_MAPPING = {
        'Input': FormFieldType.INPUT,
        'Input.Password': FormFieldType.PASSWORD,
        'Password': FormFieldType.PASSWORD,
        'Input.TextArea': FormFieldType.TEXTAREA,
        'TextArea': FormFieldType.TEXTAREA,
        'Select': FormFieldType.SELECT,
        'Cascader': FormFieldType.CASCADER,
        'Switch': FormFieldType.SWITCH,
        'Radio.Group': FormFieldType.RADIO,
        'Radio': FormFieldType.RADIO,
        'Checkbox.Group': FormFieldType.CHECKBOX,
        'Checkbox': FormFieldType.CHECKBOX,
        'DatePicker': FormFieldType.DATE_PICKER,
        'RangePicker': FormFieldType.RANGE_PICKER,
        'Upload': FormFieldType.UPLOAD,
        'InputNumber': FormFieldType.INPUT_NUMBER,
    }

    def __init__(self):
        self.form_counter = 0
        self.field_counter = 0

    def scan_file(self, file_path: str, content: str) -> List[FormInfo]:
        """扫描单个文件中的表单"""
        forms = []

        form_instances = self._find_form_instances(content)

        for form_var in form_instances:
            form_info = self._extract_form_info(file_path, content, form_var)
            if form_info:
                forms.append(form_info)
                self.form_counter += 1

        form_components = self._find_form_components(content)
        for form_match in form_components:
            form_info = self._extract_form_component_info(file_path, content, form_match)
            if form_info:
                exists = any(f.form_instance == form_info.form_instance for f in forms)
                if not exists:
                    forms.append(form_info)
                    self.form_counter += 1

        return forms

    def _find_form_instances(self, content: str) -> List[str]:
        """查找 Form.useForm() 实例"""
        instances = []

        pattern = re.compile(r'\[?\s*(\w+)\s*\]?\s*=\s*Form\.useForm\s*\(')
        for match in pattern.finditer(content):
            var_name = match.group(1)
            if var_name not in instances:
                instances.append(var_name)

        pattern2 = re.compile(r'const\s+(\w+)\s*=\s*Form\.useForm\s*\(')
        for match in pattern2.finditer(content):
            var_name = match.group(1)
            if var_name not in instances:
                instances.append(var_name)

        return instances

    def _find_form_components(self, content: str) -> List[Dict[str, Any]]:
        """查找 <Form> 组件"""
        forms = []

        pattern = re.compile(r'<Form[^>]*>')
        for match in pattern.finditer(content):
            start_pos = match.start()
            full_tag = match.group(0)

            form_match = {
                'start_pos': start_pos,
                'full_tag': full_tag,
                'start_line': content[:start_pos].count('\n') + 1
            }

            form_var = self._extract_form_var(full_tag)
            if form_var:
                form_match['form_var'] = form_var

            forms.append(form_match)

        return forms

    def _extract_form_var(self, tag: str) -> Optional[str]:
        """从 <Form form={xxx}> 中提取表单变量"""
        pattern = re.compile(r'form\s*=\s*\{([^}]+)\}')
        match = pattern.search(tag)
        if match:
            return match.group(1).strip()
        return None

    def _extract_form_info(self, file_path: str, content: str, form_var: str) -> Optional[FormInfo]:
        """提取表单信息"""
        start_line = 0
        end_line = 0

        pattern = re.compile(rf'{form_var}\s*=\s*Form\.useForm\s*\(')
        match = pattern.search(content)
        if match:
            start_line = content[:match.start()].count('\n') + 1

        pattern2 = re.compile(rf'const\s+{form_var}\s*=\s*Form\.useForm\s*\(')
        match2 = pattern2.search(content)
        if match2:
            start_line = content[:match2.start()].count('\n') + 1

        fields = self._extract_form_fields(file_path, content, form_var)

        validation_methods = self._find_validation_methods(content, form_var)
        submit_methods = self._find_submit_methods(content, form_var)

        form_id = self._generate_id(file_path, form_var)

        return FormInfo(
            id=form_id,
            name=self._generate_form_name(form_var, file_path),
            form_instance=form_var,
            file_path=file_path,
            location=Location(
                start_line=start_line,
                end_line=end_line or start_line
            ),
            fields=fields,
            validation_methods=validation_methods,
            submit_methods=submit_methods,
            metadata={}
        )

    def _extract_form_component_info(self, file_path: str, content: str, form_match: Dict[str, Any]) -> Optional[FormInfo]:
        """从 <Form> 组件提取表单信息"""
        form_var = form_match.get('form_var', 'form')
        start_line = form_match['start_line']

        form_start = form_match['start_pos']
        form_end = self._find_form_end(content, form_start)

        fields = self._extract_fields_from_form_block(
            file_path, 
            content[form_start:form_end] if form_end else content[form_start:],
            form_var,
            start_line
        )

        validation_methods = self._find_validation_methods(content, form_var)
        submit_methods = self._find_submit_methods(content, form_var)

        form_id = self._generate_id(file_path, form_var)

        return FormInfo(
            id=form_id,
            name=self._generate_form_name(form_var, file_path),
            form_instance=form_var,
            file_path=file_path,
            location=Location(
                start_line=start_line,
                end_line=content[:form_end].count('\n') + 1 if form_end else start_line
            ),
            fields=fields,
            validation_methods=validation_methods,
            submit_methods=submit_methods,
            metadata={}
        )

    def _find_form_end(self, content: str, start_pos: int) -> Optional[int]:
        """查找 </Form> 结束标签位置"""
        depth = 1
        pos = start_pos
        pattern = re.compile(r'<Form\b|</Form\s*>')
        
        while depth > 0:
            match = pattern.search(content, pos + 1)
            if not match:
                break
            
            if match.group().startswith('</Form'):
                depth -= 1
                if depth == 0:
                    return match.end()
            else:
                depth += 1
            
            pos = match.start()
        
        return None

    def _extract_form_fields(self, file_path: str, content: str, form_var: str) -> List[FormFieldInfo]:
        """提取表单字段"""
        fields = []

        form_item_pattern = re.compile(
            r'<Form\.Item[^>]*name\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</Form\.Item>',
            re.DOTALL
        )

        for match in form_item_pattern.finditer(content):
            field_name = match.group(1)
            inner_content = match.group(2)
            start_pos = match.start()
            start_line = content[:start_pos].count('\n') + 1

            label = self._extract_label(match.group(0))
            required = self._check_required(match.group(0))
            rules = self._extract_rules(match.group(0))
            field_type = self._detect_field_type(inner_content)
            placeholder = self._extract_placeholder(inner_content)

            field = FormFieldInfo(
                name=field_name,
                label=label or field_name,
                type=field_type,
                required=required,
                rules=rules,
                location=Location(
                    start_line=start_line,
                    end_line=start_line
                ),
                placeholder=placeholder,
                metadata={}
            )

            fields.append(field)
            self.field_counter += 1

        return fields

    def _extract_fields_from_form_block(self, file_path: str, form_content: str, form_var: str, base_line: int) -> List[FormFieldInfo]:
        """从表单块中提取字段"""
        return self._extract_form_fields(file_path, form_content, form_var)

    def _extract_label(self, form_item_tag: str) -> str:
        """提取 label 属性"""
        pattern = re.compile(r'label\s*=\s*\{?\s*["\']([^"\']+)["\']\s*\}?')
        match = pattern.search(form_item_tag)
        if match:
            return match.group(1)

        pattern2 = re.compile(r'label\s*=\s*\{([^}]+)\}')
        match2 = pattern2.search(form_item_tag)
        if match2:
            return match2.group(1).strip()

        return ""

    def _check_required(self, form_item_tag: str) -> bool:
        """检查是否必填"""
        if 'rules={[{required: true' in form_item_tag:
            return True
        if 'rules={[{required:true' in form_item_tag:
            return True
        if 'required: true' in form_item_tag:
            return True
        
        pattern = re.compile(r'required\s*=\s*\{?\s*true\s*\}?')
        if pattern.search(form_item_tag):
            return True

        pattern2 = re.compile(r'rules\s*=\s*\{[^}]*required\s*:\s*true')
        if pattern2.search(form_item_tag):
            return True

        return False

    def _extract_rules(self, form_item_tag: str) -> List[Dict[str, Any]]:
        """提取验证规则"""
        rules = []

        if 'required' in form_item_tag.lower():
            rules.append({
                "required": True,
                "message": "请输入"
            })

        return rules

    def _detect_field_type(self, inner_content: str) -> FormFieldType:
        """检测字段类型"""
        for component_name, field_type in self.FORM_FIELD_MAPPING.items():
            pattern = rf'<{component_name}\b'
            if re.search(pattern, inner_content):
                return field_type

        return FormFieldType.UNKNOWN

    def _extract_placeholder(self, inner_content: str) -> str:
        """提取 placeholder"""
        pattern = re.compile(r'placeholder\s*=\s*["\']([^"\']+)["\']')
        match = pattern.search(inner_content)
        if match:
            return match.group(1)
        return ""

    def _find_validation_methods(self, content: str, form_var: str) -> List[str]:
        """查找表单验证方法"""
        methods = []

        pattern = re.compile(rf'{form_var}\.validateFields\s*\(')
        for match in pattern.finditer(content):
            if f'{form_var}.validateFields' not in methods:
                methods.append(f'{form_var}.validateFields')

        pattern2 = re.compile(rf'{form_var}\.validateField\s*\(')
        for match in pattern2.finditer(content):
            if f'{form_var}.validateField' not in methods:
                methods.append(f'{form_var}.validateField')

        return methods

    def _find_submit_methods(self, content: str, form_var: str) -> List[str]:
        """查找表单提交方法"""
        methods = []

        pattern = re.compile(rf'{form_var}\.getFieldsValue\s*\(')
        for match in pattern.finditer(content):
            if f'{form_var}.getFieldsValue' not in methods:
                methods.append(f'{form_var}.getFieldsValue')

        pattern2 = re.compile(rf'{form_var}\.setFieldsValue\s*\(')
        for match in pattern2.finditer(content):
            if f'{form_var}.setFieldsValue' not in methods:
                methods.append(f'{form_var}.setFieldsValue')

        return methods

    def _generate_id(self, file_path: str, form_var: str) -> str:
        """生成唯一ID"""
        key = f"{file_path}#{form_var}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def _generate_form_name(self, form_var: str, file_path: str) -> str:
        """生成表单名称"""
        from pathlib import Path
        file_name = Path(file_path).stem

        if form_var:
            return f"{file_name}_{form_var}"
        return file_name
