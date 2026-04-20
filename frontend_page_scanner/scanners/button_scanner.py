#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版按钮扫描器
支持多行JSX、动态渲染、各种属性模式
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    ButtonInfo, ButtonType, ActionType, Location
)


class ButtonScanner:
    """增强版按钮扫描器"""

    BUTTON_TEXT_PATTERNS = {
        r'新[增减]|添[加增]|创建': ActionType.CREATE,
        r'删[除去]|移[除去]': ActionType.DELETE,
        r'修[改辑]|编[改辑]': ActionType.UPDATE,
        r'下一[步页]|next': ActionType.NEXT_STEP,
        r'上一[步页]|prev|back': ActionType.PREV_STEP,
        r'完[成认]|确[认定]|提交|submit|finish': ActionType.SUBMIT,
        r'取[消闭]|关[闭销]|cancel|close': ActionType.CANCEL,
        r'测[试接]|连[接试]|test|connection': ActionType.TEST,
        r'保[存取]|save': ActionType.SAVE,
        r'打[开]|open': ActionType.OPEN_MODAL,
    }

    def __init__(self):
        self.button_counter = 0

    def scan_file(self, file_path: str, content: str) -> List[ButtonInfo]:
        """扫描单个文件中的按钮"""
        buttons = []

        button_matches = self._find_all_buttons(content)

        for match_info in button_matches:
            full_match = match_info['full']
            start_pos = match_info['start']
            end_pos = match_info['end']
            is_self_closing = match_info.get('is_self_closing', False)

            start_line = content[:start_pos].count('\n') + 1
            end_line = content[:end_pos].count('\n') + 1

            button_type = self._extract_button_type(full_match)
            onclick = self._extract_onclick(full_match)
            text_content = self._extract_text(full_match, is_self_closing)
            icon = self._extract_icon(full_match)
            is_danger = self._extract_danger(full_match)
            is_disabled = self._extract_disabled(full_match)

            action_type = ActionType.UNKNOWN
            if onclick:
                action_type = self._infer_action_type(onclick)
            if action_type == ActionType.UNKNOWN and text_content:
                action_type = self._infer_action_from_text(text_content)

            container_type = self._detect_container_type(content, start_pos, start_line, onclick, text_content)

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
                    "full_match": full_match[:300] if len(full_match) > 300 else full_match,
                    "is_self_closing": is_self_closing
                }
            )

            buttons.append(button)
            self.button_counter += 1

        return buttons

    def _find_all_buttons(self, content: str) -> List[Dict[str, Any]]:
        """查找所有 Button 组件，包括多行、自闭合等各种形式"""
        matches = []

        self_closing_pattern = re.compile(
            r'<Button\s+[^>]*?/>',
            re.DOTALL
        )
        for match in self_closing_pattern.finditer(content):
            matches.append({
                'full': match.group(0),
                'start': match.start(),
                'end': match.end(),
                'is_self_closing': True
            })

        open_tag_pattern = re.compile(
            r'<Button\b[^>]*>',
            re.DOTALL
        )
        for open_match in open_tag_pattern.finditer(content):
            open_tag = open_match.group(0)

            if '/>' in open_tag:
                continue

            is_already_matched = any(
                m['start'] <= open_match.start() < m['end']
                for m in matches
            )
            if is_already_matched:
                continue

            close_pos = self._find_matching_closing_tag(
                content, open_match.end(), 'Button'
            )

            if close_pos > open_match.end():
                full_match = content[open_match.start():close_pos]

                is_nested = any(
                    m['start'] > open_match.start() and m['end'] < close_pos
                    for m in matches
                )
                if not is_nested:
                    matches.append({
                        'full': full_match,
                        'start': open_match.start(),
                        'end': close_pos,
                        'is_self_closing': False
                    })

        unique_matches = []
        seen_positions = set()
        for m in sorted(matches, key=lambda x: x['start']):
            pos_key = (m['start'], m['end'])
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                unique_matches.append(m)

        return unique_matches

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

    def _extract_button_type(self, match_str: str) -> ButtonType:
        """提取按钮类型"""
        type_match = re.search(r'type\s*=\s*(?:\{?\s*["\'](primary|default|danger|link|text)["\']\s*\}?)', match_str)
        if type_match:
            type_str = type_match.group(1)
            if type_str == 'primary':
                return ButtonType.PRIMARY
            elif type_str == 'danger':
                return ButtonType.DANGER
            elif type_str == 'link':
                return ButtonType.LINK
            elif type_str == 'text':
                return ButtonType.TEXT

        danger_match = re.search(r'danger\s*=\s*\{?\s*(true|True)\s*\}?', match_str)
        if danger_match:
            return ButtonType.DANGER

        return ButtonType.DEFAULT

    def _extract_onclick(self, match_str: str) -> str:
        """提取 onClick 属性，支持各种形式"""
        patterns = [
            r'onClick\s*=\s*\{\s*([^}]+?)\s*\}(?:\s|/>|>)',
            r'onClick\s*=\s*["\']([^"\']+)["\']',
            r'onClick\s*=\s*\{([^}]+)\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, match_str, re.DOTALL)
            if match:
                onclick = match.group(1).strip()
                onclick = re.sub(r'\s+', ' ', onclick)
                return onclick

        return ""

    def _extract_text(self, match_str: str, is_self_closing: bool) -> str:
        """提取按钮文本内容"""
        if is_self_closing:
            return ""

        children_match = re.search(r'children\s*=\s*\{\s*([^}]+?)\s*\}', match_str)
        if children_match:
            text = children_match.group(1).strip()
            if text.startswith('"') or text.startswith("'"):
                text = text[1:-1]
            return text

        close_match = re.search(r'>([^<]*)</Button>', match_str)
        if close_match:
            text = close_match.group(1).strip()
            if text:
                return text

        inner_match = re.search(r'>\s*([^<]+?)\s*</Button>', match_str)
        if inner_match:
            text = inner_match.group(1).strip()
            if text and not text.startswith('<'):
                return text

        simple_text_match = re.search(r'>\s*([^<{}]+?)\s*(?:<|$)', match_str)
        if simple_text_match:
            text = simple_text_match.group(1).strip()
            if text and len(text) > 0:
                return text

        return ""

    def _extract_icon(self, match_str: str) -> Optional[str]:
        """提取图标"""
        icon_match = re.search(r'icon\s*=\s*\{<([A-Za-z]+Outlined|PlusOutlined|MinusOutlined|EditOutlined|DeleteOutlined)[^>]*>\}', match_str)
        if icon_match:
            return icon_match.group(1)

        simple_icon = re.search(r'icon\s*=\s*\{(\w+)\}', match_str)
        if simple_icon:
            return simple_icon.group(1)

        return None

    def _extract_danger(self, match_str: str) -> bool:
        """提取 danger 属性"""
        danger_match = re.search(r'danger\s*=\s*\{?\s*(true|True)\s*\}?', match_str)
        if danger_match:
            return True

        if 'danger' in match_str:
            danger_check = re.search(r'\bdanger\b', match_str)
            if danger_check:
                before_text = match_str[max(0, danger_check.start() - 20):danger_check.start()]
                after_text = match_str[danger_check.end():danger_check.end() + 10]
                if '={true}' in after_text or '={True}' in after_text:
                    return True
                if '={false}' not in after_text and '={False}' not in after_text:
                    pass

        return False

    def _extract_disabled(self, match_str: str) -> bool:
        """提取 disabled 属性"""
        disabled_match = re.search(r'disabled\s*=\s*\{?\s*(true|True|\{\s*!\s*\w+\s*\})\s*\}?', match_str)
        if disabled_match:
            return True

        disabled_simple = re.search(r'\bdisabled\s*=\s*\{', match_str)
        if disabled_simple:
            after = match_str[disabled_simple.end():disabled_simple.end() + 30]
            if 'false' not in after.lower() or '!' in after:
                pass

        return False

    def _infer_action_type(self, onclick: str) -> ActionType:
        """从 onClick 处理函数名推断操作类型"""
        onclick_lower = onclick.lower()

        if any(p in onclick_lower for p in ['next', 'handlenext', 'gonext']):
            return ActionType.NEXT_STEP
        elif any(p in onclick_lower for p in ['prev', 'back', 'handleprev', 'goback', 'previous']):
            return ActionType.PREV_STEP
        elif any(p in onclick_lower for p in ['create', 'submit', 'finish', 'handlefinish', 'handleok', 'ok', 'confirm']):
            return ActionType.SUBMIT
        elif any(p in onclick_lower for p in ['cancel', 'close', 'handlecancel', 'oncancel', 'onclose']):
            return ActionType.CANCEL
        elif any(p in onclick_lower for p in ['delete', 'remove', 'handledelete']):
            return ActionType.DELETE
        elif any(p in onclick_lower for p in ['test', 'connection', 'testconnection', 'handleconnection']):
            return ActionType.TEST
        elif any(p in onclick_lower for p in ['save', 'handlesave']):
            return ActionType.SAVE
        elif any(p in onclick_lower for p in ['provider', 'select', 'handleselect']):
            return ActionType.OPEN_MODAL
        elif any(p in onclick_lower for p in ['add', 'new', 'handleadd', 'handlenew']):
            return ActionType.CREATE
        elif any(p in onclick_lower for p in ['update', 'edit', 'modify', 'handleupdate', 'handleedit']):
            return ActionType.UPDATE

        return ActionType.UNKNOWN

    def _infer_action_from_text(self, text: str) -> ActionType:
        """从按钮文本推断操作类型"""
        text_lower = text.lower()

        for pattern, action in self.BUTTON_TEXT_PATTERNS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return action

        if text_lower in ['next', '下一步', '下一页', '>']:
            return ActionType.NEXT_STEP
        elif text_lower in ['prev', 'previous', 'back', '上一步', '上一页', '<']:
            return ActionType.PREV_STEP
        elif text_lower in ['finish', 'done', 'complete', 'submit', '完成', '确认', '提交', '确定', 'ok']:
            return ActionType.SUBMIT
        elif text_lower in ['cancel', 'close', '取消', '关闭']:
            return ActionType.CANCEL
        elif text_lower in ['delete', 'remove', '删除', '移除']:
            return ActionType.DELETE
        elif text_lower in ['test', 'connection', '测试', '连接', '测试连接']:
            return ActionType.TEST
        elif text_lower in ['save', '保存']:
            return ActionType.SAVE
        elif text_lower in ['create', 'add', 'new', '创建', '添加', '新增', '+']:
            return ActionType.CREATE

        return ActionType.UNKNOWN

    def _detect_container_type(self, content: str, start_pos: int, start_line: int, 
                                 onclick: str, text_content: str) -> str:
        """检测按钮所在的容器类型"""
        before_content = content[max(0, start_pos - 3000):start_pos]
        after_content = content[start_pos:min(len(content), start_pos + 2000)]
        combined = before_content + after_content

        if re.search(r'(Wizard|wizard|向导|步骤|Steps|steps)', combined):
            return "wizard"
        elif re.search(r'(Modal|modal|Drawer|drawer)', combined):
            return "modal"
        elif re.search(r'(Form\.Item|form\.item)', combined):
            return "form"
        elif re.search(r'(Form\.List|form\.list)', combined):
            return "form"
        elif re.search(r'(Table|table)', combined):
            return "table"
        elif re.search(r'(Card|card)', combined):
            return "card"

        if onclick:
            onclick_lower = onclick.lower()
            if any(p in onclick_lower for p in ['next', 'prev', 'test', 'finish', 'wizard']):
                return "wizard"
            elif any(p in onclick_lower for p in ['modal', 'open', 'close']):
                return "modal"

        if text_content:
            text_lower = text_content.lower()
            if any(p in text_lower for p in ['下一步', '上一步', '测试', '完成', '向导']):
                return "wizard"

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
            if 'handle' in onclick.lower():
                return onclick
            return onclick
        return f"button_{action_type.value}"
