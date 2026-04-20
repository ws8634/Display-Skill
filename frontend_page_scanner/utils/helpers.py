#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助函数模块
"""

from typing import List, Dict, Any
from pathlib import Path
import fnmatch


def should_exclude(file_path: Path, exclude_patterns: List[str]) -> bool:
    """检查文件是否应该排除"""
    for pattern in exclude_patterns:
        try:
            if file_path.match(pattern):
                return True
        except Exception:
            pass

        file_str = str(file_path)

        if pattern.startswith('**/'):
            check_pattern = pattern[3:]
            if f'/{check_pattern}/' in file_str or file_str.endswith(f'/{check_pattern}') or f'/{check_pattern}' in file_str:
                return True

        if pattern.endswith('/**'):
            check_pattern = pattern[:-3]
            if f'{check_pattern}/' in file_str:
                return True

        path_parts = file_path.parts
        for part in path_parts:
            if part == pattern or fnmatch.fnmatch(part, pattern):
                return True

        if fnmatch.fnmatch(file_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
            return True

    return False


def scan_project_files(
    project_path: str,
    include_patterns: List[str],
    exclude_patterns: List[str],
    max_files: int = 500
) -> List[str]:
    """扫描项目文件"""
    files = []
    project_dir = Path(project_path)

    pattern_files = {}
    for pattern in include_patterns:
        pattern_files[pattern] = []
        try:
            for file_path in project_dir.glob(pattern):
                if should_exclude(file_path, exclude_patterns):
                    continue

                if not file_path.is_file():
                    continue

                pattern_files[pattern].append(str(file_path))
        except Exception:
            pass

    per_pattern_limit = max_files // len(include_patterns) if include_patterns else max_files
    for pattern, pattern_file_list in pattern_files.items():
        if len(pattern_file_list) <= per_pattern_limit:
            files.extend(pattern_file_list)
        else:
            files.extend(pattern_file_list[:per_pattern_limit])

        if len(files) >= max_files:
            break

    return files
