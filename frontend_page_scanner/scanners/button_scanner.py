#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按钮扫描器
用于识别 TSX 文件中的 Ant Design Button 组件及其交互事件
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    ButtonInfo, ButtonType, ActionType, Location
)


class ButtonScanner:
    """按钮扫描器"""

    BUTTON_TEXT_PATTERNS = {
        r'[新新][增减加]': ActionType.CREATE,
        r'[添增][加增]': ActionType.CREATE,
        r'[创建建]': ActionType.CREATE,
        r'[删去][除去]': ActionType.DELETE,
        r'[移除去]': ActionType.DELETE,
        r'[修编][改辑]': ActionType.UPDATE,
        r'[下一步][页]': ActionType.NEXT_STEP,
        r'[上一步][页]': ActionType.PREV_STEP,
        r'[完确][成认]': ActionType.SUBMIT,
        r'[提交交]': ActionType.SUBMIT,
        r'[取关][消闭]': ActionType.CANCEL,
        r'[关闭闭]': ActionType.CLOSE_MODAL,
        r'[测连][试接]': ActionType.TEST,
        r'[保存存]': ActionType.SAVE,
        r'[打打][开]': ActionType.OPEN_MODAL,
    }

    def __init__(self):
        self.button_counter = 0

    def scan_file(self, file_path: str, content: str) -> List[ButtonInfo]:
        """扫描单个文件中的按钮"""
        buttons = []

        lines = content.split('\n')

        button_patterns = [
            re.compile(r'<Button[^>]*>', re.MULTILINE),
            re.compile(r'<Button\s+[^>]*?/>', re.MULTILINE),
        ]

        onclick_pattern = re.compile(r'onClick\s*=\s*\{([^}]+)\}')
        type_pattern = re.compile(r'type\s*=\s*["\'](primary|default|danger|link|text)["\']')
        danger_pattern = re.compile(r'danger\s*=\s*\{(true|false)\}')
        disabled_pattern = re.compile(r'disabled\s*=\s*\{(true|false)\}')
        icon_pattern = re.compile(r'icon\s*=\s*\{<([A-Za-z]+Outlined)[^>]*>\}')
        text_pattern = re.compile(r'>([^<]+)</Button>')

        for match in re.finditer(r'<Button[^>]*>(.*?)</Button>|<Button\s+[^>]*?/>', content, re.DOTALL):
            full_match = match.group(0)
            start_pos = match.start()
            end_pos = match.end()

            start_line = content[:start_pos].count('\n') + 1
            end_line = content[:end_pos].count('\n') + 1

            button_type = ButtonType.DEFAULT
            type_match = type_pattern.search(full_match)
            if type_match:
                type_str = type_match.group(1)
                if type_str == 'primary':
                    button_type = ButtonType.PRIMARY
                elif type_str == 'danger':
                    button_type = ButtonType.DANGER
                elif type_str == 'link':
                    button_type = ButtonType.LINK
                elif type_str == 'text':
                    button_type = ButtonType.TEXT

            is_danger = False
            danger_match = danger_pattern.search(full_match)
            if danger_match and danger_match.group(1) == 'true':
                is_danger = True
                button_type = ButtonType.DANGER

            is_disabled = False
            disabled_match = disabled_pattern.search(full_match)
            if disabled_match and disabled_match.group(1) == 'true':
                is_disabled = True

            onclick = ""
            action_type = ActionType.UNKNOWN
            onclick_match = onclick_pattern.search(full_match)
            if onclick_match:
                onclick = onclick_match.group(1).strip()
                action_type = self._infer_action_type(onclick)

            icon = None
            icon_match = icon_pattern.search(full_match)
            if icon_match:
                icon = icon_match.group(1)

            text_content = ""
            if 'children' in full_match:
                children_match = re.search(r'children\s*=\s*\{([^}]+)\}', full_match)
                if children_match:
                    text_content = children_match.group(1).strip()
            if not text_content and '</Button>' in full_match:
                text_match = text_pattern.search(full_match)
                if text_match:
                    text_content = text_match.group(1).strip()

            if not text_content:
                text_match = re.search(r'>\s*([^<]+?)\s*</Button>', full_match)
                if text_match:
                    text_content = text_match.group(1).strip()

            if text_content and action_type == ActionType.UNKNOWN:
                action_type = self._infer_action_from_text(text_content)

            container_type = self._detect_container_type(content, start_pos, start_line)

            button_id = self._generate_id(file_path, start_line, onclick, text_content)

            button = ButtonInfo(
                id=button_id,
                name=self._generate_name(text_content, onclick, action_type),
                type=button_type,
                action_type=action_type,
                onClick=onclick,
                file_path=file_path,
                location=Location(
                    start_line=start_line,
                    end_line=end_line
                ),
                text_content=text_content,
                icon=icon,
                disabled=is_disabled,
                danger=is_danger,
                container_type=container_type,
                metadata={
                    "full_match": full_match[:200] if len(full_match) > 200 else full_match
                }
            )

            buttons.append(button)
            self.button_counter += 1

        return buttons

    def _infer_action_type(self, onclick: str) -> ActionType:
        """从 onClick 处理函数名推断操作类型"""
        onclick_lower = onclick.lower()

        if any(p in onclick_lower for p in ['next', 'handlenext']):
            return ActionType.NEXT_STEP
        elif any(p in onclick_lower for p in ['prev', 'back', 'handleprev']):
            return ActionType.PREV_STEP
        elif any(p in onclick_lower for p in ['create', 'submit', 'finish', 'handlefinish']):
            return ActionType.SUBMIT
        elif any(p in onclick_lower for p in ['cancel', 'close', 'handlecancel']):
            return ActionType.CANCEL
        elif any(p in onclick_lower for p in ['delete', 'remove']):
            return ActionType.DELETE
        elif any(p in onclick_lower for p in ['test', 'connection', 'testconnection']):
            return ActionType.TEST
        elif any(p in onclick_lower for p in ['save']):
            return ActionType.SAVE
        elif any(p in onclick_lower for p in ['provider', 'select']):
            return ActionType.OPEN_MODAL
        elif any(p in onclick_lower for p in ['add', 'new']):
            return ActionType.CREATE
        elif any(p in onclick_lower for p in ['update', 'edit', 'modify']):
            return ActionType.UPDATE

        return ActionType.UNKNOWN

    def _infer_action_from_text(self, text: str) -> ActionType:
        """从按钮文本推断操作类型"""
        text_lower = text.lower()

        for pattern, action in self.BUTTON_TEXT_PATTERNS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return action

        if text_lower in ['next', '下一步', '下一页']:
            return ActionType.NEXT_STEP
        elif text_lower in ['prev', 'previous', 'back', '上一步', '上一页']:
            return ActionType.PREV_STEP
        elif text_lower in ['finish', 'done', 'complete', 'submit', '完成', '确认', '提交']:
            return ActionType.SUBMIT
        elif text_lower in ['cancel', 'close', '取消', '关闭']:
            return ActionType.CANCEL
        elif text_lower in ['delete', 'remove', '删除', '移除']:
            return ActionType.DELETE
        elif text_lower in ['test', 'connection', '测试', '连接', '测试连接']:
            return ActionType.TEST
        elif text_lower in ['save', '保存']:
            return ActionType.SAVE

        return ActionType.UNKNOWN

    def _detect_container_type(self, content: str, start_pos: int, start_line: int) -> str:
        """检测按钮所在的容器类型"""
        before_content = content[max(0, start_pos - 2000):start_pos]
        after_content = content[start_pos:min(len(content), start_pos + 1000)]
        combined = before_content + after_content

        if re.search(r'(Wizard|向导|步骤|Steps)', combined):
            return "wizard"
        elif re.search(r'(Modal|modal|Drawer|drawer)', combined):
            return "modal"
        elif re.search(r'(Form|form)', combined):
            return "form"
        elif re.search(r'(Table|table)', combined):
            return "table"
        elif re.search(r'(Card|card)', combined):
            return "card"

        return "unknown"

    def _generate_id(self, file_path: str, line: int, onclick: str, text: str) -> str:
        """生成唯一ID"""
        key = f"{file_path}#{line}#{onclick}#{text}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def _generate_name(self, text: str, onclick: str, action_type: ActionType) -> str:
        """生成按钮名称"""
        if text:
            return text.strip()
        if onclick:
            return onclick
        return f"button_{action_type.value}"
