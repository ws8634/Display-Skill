#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API调用扫描器
用于识别 TSX 文件中的 API 调用模式
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    ApiCallInfo, Location
)


class ApiCallScanner:
    """API调用扫描器"""

    def __init__(self):
        self.api_counter = 0

    def scan_file(self, file_path: str, content: str) -> List[ApiCallInfo]:
        """扫描单个文件中的API调用"""
        api_calls = []

        api_calls.extend(self._find_request_patterns(file_path, content))
        api_calls.extend(self._find_fetch_patterns(file_path, content))
        api_calls.extend(self._find_axios_patterns(file_path, content))
        api_calls.extend(self._find_api_function_calls(file_path, content))

        seen = set()
        unique_calls = []
        for call in api_calls:
            key = f"{call.method}:{call.path}:{call.location.start_line}"
            if key not in seen:
                seen.add(key)
                unique_calls.append(call)
                self.api_counter += 1

        return unique_calls

    def _find_request_patterns(self, file_path: str, content: str) -> List[ApiCallInfo]:
        """查找 apiPost / apiRequest 等请求模式"""
        calls = []

        patterns = [
            (r'(apiPost|apiRequest)\s*\(\s*["\']([^"\']+)["\']', 'POST'),
            (r'(apiGet|apiRequest)\s*\(\s*["\']([^"\']+)["\']', 'GET'),
            (r'(apiPut|apiRequest)\s*\(\s*["\']([^"\']+)["\']', 'PUT'),
            (r'(apiDelete|apiRequest)\s*\(\s*["\']([^"\']+)["\']', 'DELETE'),
            (r'(apiPatch|apiRequest)\s*\(\s*["\']([^"\']+)["\']', 'PATCH'),
        ]

        for pattern, default_method in patterns:
            regex = re.compile(pattern)
            for match in regex.finditer(content):
                func_name = match.group(1)
                path = match.group(2)

                start_line = content[:match.start()].count('\n') + 1
                line_content = self._get_line_content(content, start_line)

                method = self._extract_method_from_line(line_content, func_name)
                if not method:
                    if 'Post' in func_name:
                        method = 'POST'
                    elif 'Get' in func_name:
                        method = 'GET'
                    elif 'Put' in func_name:
                        method = 'PUT'
                    elif 'Delete' in func_name:
                        method = 'DELETE'
                    elif 'Patch' in func_name:
                        method = 'PATCH'
                    else:
                        method = default_method

                called_from = self._find_calling_function(content, match.start())

                api_info = ApiCallInfo(
                    id=self._generate_id(file_path, method, path, start_line),
                    method=method,
                    path=path,
                    call_type='custom_api',
                    file_path=file_path,
                    location=Location(start_line=start_line, end_line=start_line),
                    called_from=called_from,
                    payload_construction=self._extract_payload(content, match.start()),
                    metadata={
                        'function_name': func_name,
                        'line_content': line_content
                    }
                )
                calls.append(api_info)

        return calls

    def _find_fetch_patterns(self, file_path: str, content: str) -> List[ApiCallInfo]:
        """查找 fetch 调用模式"""
        calls = []

        pattern = re.compile(r'fetch\s*\(\s*["\']([^"\']+)["\']')
        for match in pattern.finditer(content):
            path = match.group(1)
            start_line = content[:match.start()].count('\n') + 1

            method = 'GET'
            call_context = content[max(0, match.start() - 50):match.start() + 500]
            method_match = re.search(r'method\s*:\s*["\'](\w+)["\']', call_context)
            if method_match:
                method = method_match.group(1).upper()

            called_from = self._find_calling_function(content, match.start())

            api_info = ApiCallInfo(
                id=self._generate_id(file_path, method, path, start_line),
                method=method,
                path=path,
                call_type='fetch',
                file_path=file_path,
                location=Location(start_line=start_line, end_line=start_line),
                called_from=called_from,
                metadata={}
            )
            calls.append(api_info)

        return calls

    def _find_axios_patterns(self, file_path: str, content: str) -> List[ApiCallInfo]:
        """查找 axios 调用模式"""
        calls = []

        patterns = [
            (r'axios\.(post|get|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']', None),
            (r'axios\s*\(\s*\{[^}]*method\s*:\s*["\'](\w+)["\'][^}]*url\s*:\s*["\']([^"\']+)["\']', None),
            (r'axios\s*\(\s*\{[^}]*url\s*:\s*["\']([^"\']+)["\'][^}]*method\s*:\s*["\'](\w+)["\']', None),
        ]

        for pattern, _ in patterns:
            regex = re.compile(pattern, re.MULTILINE | re.DOTALL)
            for match in regex.finditer(content):
                groups = match.groups()
                if len(groups) == 2:
                    if 'url' in groups[0] or 'url' in groups[1]:
                        if 'url' in match.group(0) and 'method' in match.group(0):
                            if r'url\s*:\s*["\']' in match.group(0):
                                parts = match.group(0).split('url')
                                method_match = re.search(r'method\s*:\s*["\'](\w+)["\']', match.group(0))
                                url_match = re.search(r'url\s*:\s*["\']([^"\']+)["\']', match.group(0))
                                if method_match and url_match:
                                    method = method_match.group(1).upper()
                                    path = url_match.group(1)
                                else:
                                    continue
                            else:
                                method = groups[0].upper()
                                path = groups[1]
                        else:
                            method = groups[0].upper()
                            path = groups[1]
                    else:
                        method = groups[0].upper()
                        path = groups[1]

                    start_line = content[:match.start()].count('\n') + 1
                    called_from = self._find_calling_function(content, match.start())

                    api_info = ApiCallInfo(
                        id=self._generate_id(file_path, method, path, start_line),
                        method=method,
                        path=path,
                        call_type='axios',
                        file_path=file_path,
                        location=Location(start_line=start_line, end_line=start_line),
                        called_from=called_from,
                        metadata={}
                    )
                    calls.append(api_info)

        return calls

    def _find_api_function_calls(self, file_path: str, content: str) -> List[ApiCallInfo]:
        """查找自定义 API 函数调用"""
        calls = []

        patterns = [
            (r'(create[A-Z][a-zA-Z]*|add[A-Z][a-zA-Z]*)\s*\(', 'POST'),
            (r'(update[A-Z][a-zA-Z]*|edit[A-Z][a-zA-Z]*)\s*\(', 'PUT'),
            (r'(delete[A-Z][a-zA-Z]*|remove[A-Z][a-zA-Z]*)\s*\(', 'DELETE'),
            (r'(get[A-Z][a-zA-Z]*|fetch[A-Z][a-zA-Z]*|list[A-Z][a-zA-Z]*)\s*\(', 'GET'),
        ]

        for pattern, method in patterns:
            regex = re.compile(pattern)
            for match in regex.finditer(content):
                func_name = match.group(1)

                if func_name in ['getElementById', 'getElementsByClassName', 'getElementsByTagName',
                                'getAttribute', 'getBoundingClientRect', 'getComputedStyle',
                                'addEventListener', 'removeEventListener']:
                    continue

                start_line = content[:match.start()].count('\n') + 1

                path = f"/api/{func_name[0].lower() + func_name[1:]}"

                called_from = self._find_calling_function(content, match.start())

                api_info = ApiCallInfo(
                    id=self._generate_id(file_path, method, path, start_line),
                    method=method,
                    path=path,
                    call_type='function_call',
                    file_path=file_path,
                    location=Location(start_line=start_line, end_line=start_line),
                    called_from=called_from,
                    metadata={
                        'function_name': func_name
                    }
                )
                calls.append(api_info)

        return calls

    def _extract_method_from_line(self, line_content: str, func_name: str) -> Optional[str]:
        """从行内容中提取 HTTP 方法"""
        method_map = {
            'POST': ['post', 'create', 'add', 'submit'],
            'GET': ['get', 'fetch', 'list', 'query', 'search'],
            'PUT': ['put', 'update', 'edit'],
            'DELETE': ['delete', 'remove'],
            'PATCH': ['patch'],
        }

        line_lower = line_content.lower()
        for method, keywords in method_map.items():
            for keyword in keywords:
                if keyword in line_lower:
                    return method

        return None

    def _get_line_content(self, content: str, line_number: int) -> str:
        """获取指定行的内容"""
        lines = content.split('\n')
        if 0 <= line_number - 1 < len(lines):
            return lines[line_number - 1]
        return ""

    def _find_calling_function(self, content: str, position: int) -> str:
        """查找调用 API 的函数名"""
        func_patterns = [
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
            r'(?:async\s+)?function\s+(\w+)\s*\(',
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function',
        ]

        before_content = content[:position]

        for pattern in func_patterns:
            matches = list(re.finditer(pattern, before_content))
            if matches:
                last_match = matches[-1]
                return last_match.group(1)

        return ""

    def _extract_payload(self, content: str, position: int) -> Dict[str, Any]:
        """提取请求 payload 构造信息"""
        payload = {}

        after_content = content[position:position + 500]

        data_patterns = [
            r'data\s*:\s*\{([^}]+)\}',
            r'body\s*:\s*\{([^}]+)\}',
            r'payload\s*:\s*\{([^}]+)\}',
        ]

        for pattern in data_patterns:
            match = re.search(pattern, after_content, re.MULTILINE | re.DOTALL)
            if match:
                payload_content = match.group(1)
                keys = re.findall(r'(\w+)\s*:', payload_content)
                payload['fields'] = keys

        return payload

    def _generate_id(self, file_path: str, method: str, path: str, line: int) -> str:
        """生成唯一ID"""
        key = f"{file_path}#{method}:{path}#{line}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
