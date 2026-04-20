#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端页面扫描工具 (Frontend Page Scanner)
用于扫描前端TSX页面代码，识别按钮、表单、向导等交互元素，
构建操作链用于E2E测试用例生成。
"""

from .main import FrontendPageScanner
from .models.data_models import (
    ButtonType,
    ActionType,
    FormFieldType,
    OperationStepType,
    Location,
    ButtonInfo,
    FormFieldInfo,
    FormInfo,
    StepInfo,
    ApiCallInfo,
    OperationStep,
    OperationChain,
    ScanResult
)
from .scanners.button_scanner import ButtonScanner
from .scanners.form_scanner import FormScanner
from .scanners.step_scanner import StepScanner
from .scanners.api_call_scanner import ApiCallScanner
from .builders.operation_chain_builder import OperationChainBuilder

__version__ = "1.0.0"
__all__ = [
    "FrontendPageScanner",
    "ButtonType",
    "ActionType",
    "FormFieldType",
    "OperationStepType",
    "Location",
    "ButtonInfo",
    "FormFieldInfo",
    "FormInfo",
    "StepInfo",
    "ApiCallInfo",
    "OperationStep",
    "OperationChain",
    "ScanResult",
    "ButtonScanner",
    "FormScanner",
    "StepScanner",
    "ApiCallScanner",
    "OperationChainBuilder",
]
