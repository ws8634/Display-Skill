#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作链构建器
基于扫描到的按钮、表单、步骤、API调用，构建完整的操作链
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
    """操作链构建器"""

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

        wizard_chains = self._build_wizard_chains(
            buttons, forms, steps, api_calls, file_path, content, component_name
        )
        chains.extend(wizard_chains)

        modal_chains = self._build_modal_chains(
            buttons, forms, api_calls, file_path, content, component_name
        )
        chains.extend(modal_chains)

        page_chains = self._build_page_chains(
            buttons, forms, api_calls, file_path, content, component_name
        )
        chains.extend(page_chains)

        return chains

    def _extract_component_name(self, file_path: str) -> str:
        """从文件路径提取组件名称"""
        from pathlib import Path
        file_name = Path(file_path).stem

        if file_name.endswith('Wizard'):
            return file_name
        elif file_name.endswith('Modal'):
            return file_name
        elif file_name.endswith('Drawer'):
            return file_name

        return file_name

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

        current_form = forms[0] if forms else None

        for idx, step in enumerate(step_order):
            step_buttons = [b for b in buttons if b.container_type == 'wizard']

            if idx == 0:
                first_buttons = [b for b in step_buttons if b.action_type == ActionType.OPEN_MODAL or b.action_type == ActionType.CREATE]
                for btn in first_buttons:
                    operation_steps.append(
                        OperationStep(
                            step_order=step_order_num,
                            type=OperationStepType.BUTTON_CLICK,
                            button={
                                'id': btn.id,
                                'name': btn.name,
                                'action': btn.onClick
                            },
                            description=f"点击按钮：{btn.name}"
                        )
                    )
                    step_order_num += 1

            if current_form:
                fields_in_step = self._find_fields_for_step(content, step, idx)
                if fields_in_step:
                    operation_steps.append(
                        OperationStep(
                            step_order=step_order_num,
                            type=OperationStepType.FORM_FILL,
                            form={
                                'id': current_form.id,
                                'name': current_form.name
                            },
                            fields=fields_in_step,
                            description=f"填写表单字段：{', '.join(fields_in_step)}"
                        )
                    )
                    step_order_num += 1

            next_buttons = [b for b in step_buttons if b.action_type == ActionType.NEXT_STEP]
            if next_buttons and idx < len(step_order) - 1:
                btn = next_buttons[0]
                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.BUTTON_CLICK,
                        button={
                            'id': btn.id,
                            'name': btn.name,
                            'action': btn.onClick
                        },
                        description=f"点击按钮：{btn.name}，进入下一步"
                    )
                )
                step_order_num += 1

                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.FORM_VALIDATE,
                        form={
                            'id': current_form.id if current_form else 'unknown',
                            'name': current_form.name if current_form else 'unknown'
                        },
                        description="表单验证"
                    )
                )
                step_order_num += 1

                operation_steps.append(
                    OperationStep(
                        step_order=step_order_num,
                        type=OperationStepType.STEP_NAVIGATE,
                        description=f"从步骤 {step.title} 导航到下一步"
                    )
                )
                step_order_num += 1

        test_buttons = [b for b in buttons if b.action_type == ActionType.TEST]
        for btn in test_buttons:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.name}，进行连接测试"
                )
            )
            step_order_num += 1

            test_api_calls = [a for a in api_calls if 'test' in a.path.lower() or 'test' in a.call_type.lower()]
            for api in test_api_calls:
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

        submit_buttons = [b for b in buttons if b.action_type == ActionType.SUBMIT]
        for btn in submit_buttons:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.name}，提交表单"
                )
            )
            step_order_num += 1

        create_api_calls = [a for a in api_calls if a.method in ['POST', 'PUT'] and 'test' not in a.path.lower()]
        for api in create_api_calls:
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
                name=self._generate_chain_name(component_name),
                file_path=file_path,
                steps=operation_steps,
                component_name=component_name,
                page_name=component_name,
                metadata={
                    'type': 'wizard',
                    'step_count': len(step_order),
                    'form_count': len(forms)
                }
            )

            chains.append(chain)
            self.chain_counter += 1

        return chains

    def _build_modal_chains(
        self,
        buttons: List[ButtonInfo],
        forms: List[FormInfo],
        api_calls: List[ApiCallInfo],
        file_path: str,
        content: str,
        component_name: str
    ) -> List[OperationChain]:
        """构建模态框操作链"""
        chains = []

        modal_buttons = [b for b in buttons if b.container_type == 'modal']

        if not modal_buttons:
            return chains

        operation_steps: List[OperationStep] = []
        step_order_num = 1

        open_buttons = [b for b in modal_buttons if b.action_type in [ActionType.CREATE, ActionType.UPDATE, ActionType.OPEN_MODAL]]
        for btn in open_buttons:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.name}，打开模态框"
                )
            )
            step_order_num += 1

            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.MODAL_OPEN,
                    description=f"模态框打开"
                )
            )
            step_order_num += 1

        if forms:
            for form in forms:
                if form.fields:
                    operation_steps.append(
                        OperationStep(
                            step_order=step_order_num,
                            type=OperationStepType.FORM_FILL,
                            form={
                                'id': form.id,
                                'name': form.name
                            },
                            fields=[f.name for f in form.fields],
                            description=f"填写表单：{form.name}"
                        )
                    )
                    step_order_num += 1

        submit_buttons = [b for b in modal_buttons if b.action_type == ActionType.SUBMIT]
        for btn in submit_buttons:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.name}，提交表单"
                )
            )
            step_order_num += 1

            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.FORM_VALIDATE,
                    form={
                        'id': forms[0].id if forms else 'unknown',
                        'name': forms[0].name if forms else 'unknown'
                    },
                    description="表单验证"
                )
            )
            step_order_num += 1

        for api in api_calls:
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

        cancel_buttons = [b for b in modal_buttons if b.action_type == ActionType.CANCEL]
        for btn in cancel_buttons:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.name}，取消操作"
                )
            )
            step_order_num += 1

            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.MODAL_CLOSE,
                    description="模态框关闭"
                )
            )
            step_order_num += 1

        if operation_steps:
            chain_id = self._generate_id(file_path, component_name, 'modal')

            chain = OperationChain(
                id=chain_id,
                name=self._generate_chain_name(component_name),
                file_path=file_path,
                steps=operation_steps,
                component_name=component_name,
                page_name=component_name,
                metadata={
                    'type': 'modal',
                    'form_count': len(forms)
                }
            )

            chains.append(chain)
            self.chain_counter += 1

        return chains

    def _build_page_chains(
        self,
        buttons: List[ButtonInfo],
        forms: List[FormInfo],
        api_calls: List[ApiCallInfo],
        file_path: str,
        content: str,
        component_name: str
    ) -> List[OperationChain]:
        """构建页面操作链（简单按钮-表单-API链）"""
        chains = []

        other_buttons = [b for b in buttons if b.container_type == 'unknown']

        if not other_buttons:
            return chains

        operation_steps: List[OperationStep] = []
        step_order_num = 1

        for btn in other_buttons:
            operation_steps.append(
                OperationStep(
                    step_order=step_order_num,
                    type=OperationStepType.BUTTON_CLICK,
                    button={
                        'id': btn.id,
                        'name': btn.name,
                        'action': btn.onClick
                    },
                    description=f"点击按钮：{btn.name}"
                )
            )
            step_order_num += 1

        if operation_steps:
            chain_id = self._generate_id(file_path, component_name, 'page')

            chain = OperationChain(
                id=chain_id,
                name=self._generate_chain_name(component_name),
                file_path=file_path,
                steps=operation_steps,
                component_name=component_name,
                page_name=component_name,
                metadata={
                    'type': 'page'
                }
            )

            chains.append(chain)
            self.chain_counter += 1

        return chains

    def _find_fields_for_step(self, content: str, step: StepInfo, step_index: int) -> List[str]:
        """查找步骤对应的表单字段"""
        fields = []

        step_title = step.title.lower()

        if '选择' in step_title or 'select' in step_title:
            return fields

        if '基本信息' in step_title or 'basic' in step_title:
            fields.extend(['name', 'type', 'region', 'namespace'])
        elif '配置' in step_title or 'config' in step_title:
            fields.extend(['endpoint', 'accessKey', 'secretKey', 'apiToken'])
        elif '计算' in step_title or 'compute' in step_title:
            fields.extend(['cpu', 'memory'])
        elif '存储' in step_title or 'storage' in step_title or 'disk' in step_title:
            fields.extend(['rootSize', 'extraDisks'])
        elif '网络' in step_title or 'network' in step_title:
            fields.extend(['netMode', 'subnet', 'ipAddress'])
        elif '登录' in step_title or 'login' in step_title or '凭据' in step_title:
            fields.extend(['loginMethod', 'loginPassword', 'sshNames'])
        elif '高级' in step_title or 'advanced' in step_title:
            fields.extend(['runStrategy', 'evictionStrategy', 'bootUseEfi'])

        return fields

    def _generate_chain_name(self, component_name: str) -> str:
        """生成操作链名称"""
        if 'Wizard' in component_name:
            return f"{component_name.replace('Wizard', '')}创建流程"
        elif 'Modal' in component_name:
            return f"{component_name.replace('Modal', '')}操作流程"
        return f"{component_name}操作流程"

    def _generate_id(self, file_path: str, component_name: str, chain_type: str) -> str:
        """生成唯一ID"""
        key = f"{file_path}#{component_name}#{chain_type}#{self.chain_counter}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
