#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端页面扫描数据模型
定义按钮、表单、步骤、API调用、操作链等数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class ButtonType(Enum):
    PRIMARY = "primary"
    DEFAULT = "default"
    DANGER = "danger"
    LINK = "link"
    TEXT = "text"


class ActionType(Enum):
    CREATE = "create"
    DELETE = "delete"
    UPDATE = "update"
    NEXT_STEP = "next_step"
    PREV_STEP = "prev_step"
    SUBMIT = "submit"
    CANCEL = "cancel"
    TEST = "test"
    SAVE = "save"
    OPEN_MODAL = "open_modal"
    CLOSE_MODAL = "close_modal"
    NAVIGATE = "navigate"
    UNKNOWN = "unknown"


class FormFieldType(Enum):
    INPUT = "input"
    PASSWORD = "password"
    TEXTAREA = "textarea"
    SELECT = "select"
    CASCADER = "cascader"
    SWITCH = "switch"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    DATE_PICKER = "date_picker"
    RANGE_PICKER = "range_picker"
    UPLOAD = "upload"
    INPUT_NUMBER = "input_number"
    UNKNOWN = "unknown"


class OperationStepType(Enum):
    BUTTON_CLICK = "button_click"
    FORM_FILL = "form_fill"
    FORM_VALIDATE = "form_validate"
    STEP_NAVIGATE = "step_navigate"
    API_CALL = "api_call"
    MODAL_OPEN = "modal_open"
    MODAL_CLOSE = "modal_close"


@dataclass
class Location:
    start_line: int
    end_line: int
    start_column: int = 0
    end_column: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_column": self.start_column,
            "end_column": self.end_column
        }


@dataclass
class ButtonInfo:
    id: str
    name: str
    type: ButtonType
    action_type: ActionType
    onClick: str
    file_path: str
    location: Location
    text_content: str = ""
    icon: Optional[str] = None
    disabled: bool = False
    danger: bool = False
    container_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "action_type": self.action_type.value,
            "onClick": self.onClick,
            "file_path": self.file_path,
            "location": self.location.to_dict(),
            "text_content": self.text_content,
            "icon": self.icon,
            "disabled": self.disabled,
            "danger": self.danger,
            "container_type": self.container_type,
            "metadata": self.metadata
        }


@dataclass
class FormFieldInfo:
    name: str
    label: str
    type: FormFieldType
    required: bool
    rules: List[Dict[str, Any]]
    location: Location
    placeholder: str = ""
    options: List[Dict[str, Any]] = field(default_factory=list)
    default_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "type": self.type.value,
            "required": self.required,
            "rules": self.rules,
            "location": self.location.to_dict(),
            "placeholder": self.placeholder,
            "options": self.options,
            "default_value": self.default_value,
            "metadata": self.metadata
        }


@dataclass
class FormInfo:
    id: str
    name: str
    form_instance: str
    file_path: str
    location: Location
    fields: List[FormFieldInfo] = field(default_factory=list)
    validation_methods: List[str] = field(default_factory=list)
    submit_methods: List[str] = field(default_factory=list)
    layout: str = "vertical"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "form_instance": self.form_instance,
            "file_path": self.file_path,
            "location": self.location.to_dict(),
            "fields": [f.to_dict() for f in self.fields],
            "validation_methods": self.validation_methods,
            "submit_methods": self.submit_methods,
            "layout": self.layout,
            "metadata": self.metadata
        }


@dataclass
class StepInfo:
    id: str
    wizard_name: str
    step_index: int
    title: str
    file_path: str
    location: Location
    next_step: Optional[int] = None
    prev_step: Optional[int] = None
    buttons_in_step: List[str] = field(default_factory=list)
    form_fields_in_step: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "wizard_name": self.wizard_name,
            "step_index": self.step_index,
            "title": self.title,
            "file_path": self.file_path,
            "location": self.location.to_dict(),
            "next_step": self.next_step,
            "prev_step": self.prev_step,
            "buttons_in_step": self.buttons_in_step,
            "form_fields_in_step": self.form_fields_in_step,
            "description": self.description,
            "metadata": self.metadata
        }


@dataclass
class ApiCallInfo:
    id: str
    method: str
    path: str
    call_type: str
    file_path: str
    location: Location
    called_from: str = ""
    payload_construction: Dict[str, Any] = field(default_factory=dict)
    response_handling: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "method": self.method,
            "path": self.path,
            "call_type": self.call_type,
            "file_path": self.file_path,
            "location": self.location.to_dict(),
            "called_from": self.called_from,
            "payload_construction": self.payload_construction,
            "response_handling": self.response_handling,
            "metadata": self.metadata
        }


@dataclass
class OperationStep:
    step_order: int
    type: OperationStepType
    button: Optional[Dict[str, Any]] = None
    form: Optional[Dict[str, Any]] = None
    api_call: Optional[Dict[str, Any]] = None
    fields: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "step_order": self.step_order,
            "type": self.type.value,
            "description": self.description,
            "metadata": self.metadata
        }
        if self.button:
            result["button"] = self.button
        if self.form:
            result["form"] = self.form
        if self.fields:
            result["fields"] = self.fields
        if self.api_call:
            result["api_call"] = self.api_call
        return result


@dataclass
class OperationChain:
    id: str
    name: str
    file_path: str
    steps: List[OperationStep] = field(default_factory=list)
    page_name: str = ""
    component_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        button_clicks = len([s for s in self.steps if s.type == OperationStepType.BUTTON_CLICK])
        form_fills = len([s for s in self.steps if s.type == OperationStepType.FORM_FILL])
        api_calls = len([s for s in self.steps if s.type == OperationStepType.API_CALL])

        return {
            "id": self.id,
            "name": self.name,
            "file_path": self.file_path,
            "steps": [s.to_dict() for s in self.steps],
            "page_name": self.page_name,
            "component_name": self.component_name,
            "metadata": {
                "total_steps": len(self.steps),
                "button_clicks": button_clicks,
                "form_fills": form_fills,
                "api_calls": api_calls,
                **self.metadata
            }
        }


@dataclass
class ScanResult:
    skill_version: str = "1.0"
    scan_type: str = "frontend_interaction"
    buttons: List[ButtonInfo] = field(default_factory=list)
    forms: List[FormInfo] = field(default_factory=list)
    steps: List[StepInfo] = field(default_factory=list)
    api_calls: List[ApiCallInfo] = field(default_factory=list)
    operation_chains: List[OperationChain] = field(default_factory=list)
    files_scanned: List[str] = field(default_factory=list)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_files_scanned": len(self.files_scanned),
            "total_buttons": len(self.buttons),
            "total_forms": len(self.forms),
            "total_steps": len(self.steps),
            "total_api_calls": len(self.api_calls),
            "total_operation_chains": len(self.operation_chains)
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_version": self.skill_version,
            "scan_type": self.scan_type,
            "summary": self.get_summary(),
            "buttons": [b.to_dict() for b in self.buttons],
            "forms": [f.to_dict() for f in self.forms],
            "steps": [s.to_dict() for s in self.steps],
            "api_calls": [a.to_dict() for a in self.api_calls],
            "operation_chains": [c.to_dict() for c in self.operation_chains],
            "files_scanned": self.files_scanned
        }
