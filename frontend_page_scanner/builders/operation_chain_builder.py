#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版操作链构建器
基于扫描到的按钮、表单、步骤、API调用，构建完整的操作链
不依赖于 container_type，而是通过关联分析来构建操作链
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    OperationChain, OperationStep, OperationStepType,
    ButtonInfo, FormInfo, StepInfo, ApiCallInfo,
    ButtonType, ActionType, FormFieldType,
    Location, ScanResult
)


class OperationChainBuilder:
    """增强版操作链构建器"""

    BUTTON_ACTION_KEYWORDS = {
        '创建': ActionType.CREATE,
        '新增': ActionType.CREATE,
        '添加': ActionType.CREATE,
        '保存': ActionType.SAVE,
        '编辑': ActionType.UPDATE,
        '修改': ActionType.UPDATE,
        '更新': ActionType.UPDATE,
        '删除': ActionType.DELETE,
        '移除': ActionType.DELETE,
        '下一步': ActionType.NEXT_STEP,
        '上一步': ActionType.PREV_STEP,
        '提交': ActionType.SUBMIT,
        '确认': ActionType.SUBMIT,
        '确定': ActionType.SUBMIT,
        '完成': ActionType.SUBMIT,
        '取消': ActionType.CANCEL,
        '关闭': ActionType.CLOSE_MODAL,
        '测试': ActionType.TEST,
        '连接测试': ActionType.TEST,
        '验证': ActionType.TEST,
        '检查': ActionType.TEST,
        '打开': ActionType.OPEN_MODAL,
        '查看': ActionType.OPEN_MODAL,
        '详情': ActionType.OPEN_MODAL,
    }

    def __init__(self):
        self.chain_counter = 0

    def build_chains(
        self,
        buttons: List[ButtonInfo],
        forms: List[FormInfo],
        steps: List[StepInfo],
        api_calls: List[ApiCallInfo],
        file_path: str,
        content: str
    ) -> List[OperationChain]:
        """构建操作链"""
        chains = []

        component_name = self._extract_component_name(file_path)

        if steps:
            wizard_chains = self._build_wizard_chains(
                buttons, forms, steps, api_calls, file_path, content, component_name
            )
            chains.extend(wizard_chains)

        if forms and not steps:
            form_chains = self._build_form_chains(
                buttons, forms, api_calls, file_path, content, component_name
            )
            chains.extend(form_chains)

        if buttons and not forms and not steps:
            button_chains = self._build_button_chains(
                buttons, api_calls, file_path, content, component_name
            )
            chains.extend(button_chains)

        return chains

    def _extract_component_name(self, file_path: str) -> str:
        """从文件路径提取组件名称"""
        file_name = Path(file_path).stem

        if file_name.endswith('Wizard'):
            return file_name
        elif file_name.endswith('Modal'):
            return file_name
        elif file_name.endswith('Drawer'):
            return file_name

        return file_name

    def _infer_action_from_button_text(self, text: str) -> ActionType:
        """从按钮文本推断动作类型"""
        if not text:
            return ActionType.UNKNOWN

        for keyword, action_type in self.BUTTON_ACTION_KEYWORDS.items():
            if keyword in text:
                return action_type

        if '确定' in text or '完成' in text:
            return ActionType.SUBMIT
        elif '取消' in text or '关闭' in text:
            return ActionType.CANCEL

        return ActionType.UNKNOWN

    def _build_wizard_chains(
        self,
        buttons: List[ButtonInfo],
        forms: List[FormInfo],
        steps: List[StepInfo],
        api_calls: List[ApiCallInfo],
        file_path: str,
        content: str,
        component_name: str
    ) -> List[OperationChain]:
        """构建向导操作链"""
        chains = []

        if not steps:
            return chains

        step_order = sorted(steps, key=lambda s: s.step_index)

        operation_steps: List[OperationStep] = []
        step_order_num = 1

        create_buttons = self._find_buttons_by_action(buttons, ['创建', '新增', '添加'])
        for btn in create_buttons[:1]:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'text': btn.text_content,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.text_content or btn.name}"
                )
            )
            step_order_num += 1

        for idx, step in enumerate(step_order):
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.STEP_NAVIGATE,
                    description=f"进入步骤 {idx + 1}：{step.title}"
                )
            )
            step_order_num += 1

            if forms:
                for form in forms:
                    if form.fields:
                        step_fields = self._get_fields_for_step(form, step, idx, content)
                        if step_fields:
                            operation_steps.append(
                                OperationStep(
                                    step_order=step_order_num,
                                    type=OperationStepType.FORM_FILL,
                                    form={
                                        'id': form.id,
                                        'name': form.name
                                    },
                                    fields=step_fields,
                                    description=f"在步骤 {step.title} 中填写表单：{', '.join(step_fields[:5])}{'...' if len(step_fields) > 5 else ''}"
                                )
                            )
                            step_order_num += 1

            next_buttons = self._find_buttons_by_action(buttons, ['下一步', '继续'])
            if next_buttons and idx < len(step_order) - 1:
                btn = next_buttons[0]
                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.BUTTON_CLICK,
                        button={
                            'id': btn.id,
                            'name': btn.name,
                            'text': btn.text_content,
                            'action': btn.onClick
                        },
                        description=f"点击按钮：{btn.text_content or '下一步'}"
                    )
                )
                step_order_num += 1

                if forms:
                    operation_steps.append(
                        OperationStep(
                            step_order=step_order_num,
                            type=OperationStepType.FORM_VALIDATE,
                            form={
                                'id': forms[0].id if forms else 'unknown',
                                'name': forms[0].name if forms else 'unknown'
                            },
                            description=f"表单验证：当前步骤 {step.title}"
                        )
                    )
                    step_order_num += 1

        test_buttons = self._find_buttons_by_action(buttons, ['测试', '验证', '检查'])
        for btn in test_buttons:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'text': btn.text_content,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.text_content or '测试'}"
                )
            )
            step_order_num += 1

            test_api_calls = [a for a in api_calls if 'test' in a.path.lower() or 'test' in a.call_type.lower()]
            for api in test_api_calls[:2]:
                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.API_CALL,
                        api_call={
                            'id': api.id,
                            'method': api.method,
                            'path': api.path
                        },
                        description=f"调用 API：{api.method} {api.path}"
                    )
                )
                step_order_num += 1

        submit_buttons = self._find_buttons_by_action(buttons, ['提交', '确认', '确定', '完成'])
        for btn in submit_buttons[:1]:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'text': btn.text_content,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.text_content or '提交'}"
                )
            )
            step_order_num += 1

        create_api_calls = [a for a in api_calls if a.method in ['POST', 'PUT', 'PATCH'] and 'test' not in a.path.lower()]
        for api in create_api_calls[:3]:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.API_CALL,
                    api_call={
                        'id': api.id,
                        'method': api.method,
                        'path': api.path
                    },
                    description=f"调用 API：{api.method} {api.path}"
                )
            )
            step_order_num += 1

        if operation_steps:
            chain_id = self._generate_id(file_path, component_name, 'wizard')

            chain = OperationChain(
                id=chain_id,
                name=self._generate_chain_name(component_name, 'wizard'),
                file_path=file_path,
                steps=operation_steps,
                component_name=component_name,
                page_name=component_name,
                metadata={
                    'type': 'wizard',
                    'step_count': len(step_order),
                    'form_count': len(forms),
                    'button_count': len(buttons),
                    'api_count': len(api_calls)
                }
            )

            chains.append(chain)
            self.chain_counter += 1

        return chains

    def _build_form_chains(
        self,
        buttons: List[ButtonInfo],
        forms: List[FormInfo],
        api_calls: List[ApiCallInfo],
        file_path: str,
        content: str,
        component_name: str
    ) -> List[OperationChain]:
        """构建表单操作链"""
        chains = []

        for form_idx, form in enumerate(forms):
            operation_steps: List[OperationStep] = []
            step_order_num = 1

            open_buttons = self._find_buttons_related_to_form(buttons, form, content)
            for btn in open_buttons[:2]:
                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.BUTTON_CLICK,
                        button={
                            'id': btn.id,
                            'name': btn.name,
                            'text': btn.text_content,
                            'action': btn.onClick
                        },
                        description=f"点击按钮：{btn.text_content or btn.name}，打开表单"
                    )
                )
                step_order_num += 1

            if form.fields:
                field_names = [f.name for f in form.fields]
                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.FORM_FILL,
                        form={
                            'id': form.id,
                            'name': form.name
                        },
                        fields=field_names,
                        description=f"填写表单 {form.name}：{', '.join(field_names[:5])}{'...' if len(field_names) > 5 else ''}"
                    )
                )
                step_order_num += 1

            submit_buttons = self._find_buttons_by_action(buttons, ['提交', '确认', '确定', '保存'])
            for btn in submit_buttons[:1]:
                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.BUTTON_CLICK,
                        button={
                            'id': btn.id,
                            'name': btn.name,
                            'text': btn.text_content,
                            'action': btn.onClick
                        },
                        description=f"点击按钮：{btn.text_content or '提交'}"
                    )
                )
                step_order_num += 1

                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.FORM_VALIDATE,
                        form={
                            'id': form.id,
                            'name': form.name
                        },
                        description=f"表单验证：{form.name}"
                    )
                )
                step_order_num += 1

            for api in api_calls[:3]:
                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.API_CALL,
                        api_call={
                            'id': api.id,
                            'method': api.method,
                            'path': api.path
                        },
                        description=f"调用 API：{api.method} {api.path}"
                    )
                )
                step_order_num += 1

            if operation_steps:
                chain_id = self._generate_id(file_path, component_name, f'form_{form_idx}')

                chain = OperationChain(
                    id=chain_id,
                    name=self._generate_chain_name(component_name, 'form'),
                    file_path=file_path,
                    steps=operation_steps,
                    component_name=component_name,
                    page_name=component_name,
                    metadata={
                        'type': 'form',
                        'form_name': form.name,
                        'field_count': len(form.fields)
                    }
                )

                chains.append(chain)
                self.chain_counter += 1

        return chains

    def _build_button_chains(
        self,
        buttons: List[ButtonInfo],
        api_calls: List[ApiCallInfo],
        file_path: str,
        content: str,
        component_name: str
    ) -> List[OperationChain]:
        """构建按钮操作链"""
        chains = []

        if not buttons:
            return chains

        operation_steps: List[OperationStep] = []
        step_order_num = 1

        for btn in buttons[:10]:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'text': btn.text_content,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.text_content or btn.name}"
                )
            )
            step_order_num += 1

        if operation_steps:
            chain_id = self._generate_id(file_path, component_name, 'buttons')

            chain = OperationChain(
                id=chain_id,
                name=self._generate_chain_name(component_name, 'buttons'),
                file_path=file_path,
                steps=operation_steps,
                component_name=component_name,
                page_name=component_name,
                metadata={
                    'type': 'buttons',
                    'button_count': len(buttons)
                }
            )

            chains.append(chain)
            self.chain_counter += 1

        return chains

    def _find_buttons_by_action(self, buttons: List[ButtonInfo], keywords: List[str]) -> List[ButtonInfo]:
        """按关键词查找按钮"""
        result = []
        for btn in buttons:
            text = (btn.text_content or '').lower()
            onClick = (btn.onClick or '').lower()
            for keyword in keywords:
                if keyword.lower() in text or keyword.lower() in onClick:
                    result.append(btn)
                    break
        return result

    def _find_buttons_related_to_form(self, buttons: List[ButtonInfo], form: FormInfo, content: str) -> List[ButtonInfo]:
        """查找与表单相关的按钮"""
        related = []
        form_name = form.name.lower()

        for btn in buttons:
            text = (btn.text_content or '').lower()
            onClick = (btn.onClick or '').lower()

            if any(k in text for k in ['新增', '创建', '编辑', '修改', '打开', '查看', '详情']):
                related.append(btn)
            elif any(k in onClick for k in ['showModal', 'openModal', 'open', 'show', 'create', 'edit']):
                related.append(btn)

        return related

    def _get_fields_for_step(self, form: FormInfo, step: StepInfo, step_index: int, content: str) -> List[str]:
        """获取步骤对应的表单字段"""
        all_fields = [f.name for f in form.fields]

        if not all_fields:
            return []

        step_title = step.title.lower()

        fields_per_step = max(1, len(all_fields) // max(1, step_index + 2))

        start_idx = step_index * fields_per_step
        end_idx = start_idx + fields_per_step

        if step_index == 0:
            if '选择' in step_title or 'select' in step_title:
                return [f for f in all_fields if 'type' in f.lower() or 'provider' in f.lower() or 'region' in f.lower()][:fields_per_step]
            elif '基本' in step_title or 'basic' in step_title:
                return [f for f in all_fields if 'name' in f.lower() or 'alias' in f.lower()][:fields_per_step]

        if '配置' in step_title or 'config' in step_title:
            return [f for f in all_fields if 'access' in f.lower() or 'key' in f.lower() or 'token' in f.lower() or 'endpoint' in f.lower()][:fields_per_step] or all_fields[start_idx:end_idx]

        if '计算' in step_title or 'compute' in step_title:
            return [f for f in all_fields if 'cpu' in f.lower() or 'memory' in f.lower()][:fields_per_step] or all_fields[start_idx:end_idx]

        if '存储' in step_title or 'storage' in step_title or 'disk' in step_title:
            return [f for f in all_fields if 'disk' in f.lower() or 'size' in f.lower() or 'volume' in f.lower()][:fields_per_step] or all_fields[start_idx:end_idx]

        if '网络' in step_title or 'network' in step_title:
            return [f for f in all_fields if 'net' in f.lower() or 'ip' in f.lower() or 'subnet' in f.lower()][:fields_per_step] or all_fields[start_idx:end_idx]

        if '登录' in step_title or 'login' in step_title or '凭据' in step_title:
            return [f for f in all_fields if 'login' in f.lower() or 'password' in f.lower() or 'ssh' in f.lower()][:fields_per_step] or all_fields[start_idx:end_idx]

        if '高级' in step_title or 'advanced' in step_title:
            return [f for f in all_fields if 'strategy' in f.lower() or 'efi' in f.lower() or 'advanced' in f.lower()][:fields_per_step] or all_fields[start_idx:end_idx]

        return all_fields[start_idx:end_idx]

    def _generate_chain_name(self, component_name: str, chain_type: str) -> str:
        """生成操作链名称"""
        if chain_type == 'wizard':
            if 'Wizard' in component_name:
                return f"{component_name.replace('Wizard', '')}创建流程"
            return f"{component_name}向导流程"
        elif chain_type == 'form':
            if 'Modal' in component_name:
                return f"{component_name.replace('Modal', '')}表单操作流程"
            return f"{component_name}表单流程"
        else:
            return f"{component_name}操作流程"

    def _generate_id(self, file_path: str, component_name: str, chain_type: str) -> str:
        """生成唯一ID"""
        key = f"{file_path}#{component_name}#{chain_type}#{self.chain_counter}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
