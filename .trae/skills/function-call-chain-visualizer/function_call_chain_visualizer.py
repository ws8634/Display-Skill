#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
函数调用链可视化器
用于从JSON文件中读取函数调用链数据，并将其以可视化的方式展示出来。

支持两种输出格式：
1. MDD格式：生成Markdown兼容的格式，可直接在Markdown查看器中渲染
2. Graph格式：生成知识图谱结构，适合页面交互式展示

支持三种名称显示类型：
1. 英文函数名：仅显示英文函数名
2. 中文翻译名称：仅显示中文翻译名称（无中文时回退到英文）
3. 中英文都显示：同时显示英文和中文名称
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional


class FunctionCallChainVisualizer:
    """函数调用链可视化器"""
    
    def __init__(self, json_file_path: str, display_type: str, output_format: str):
        """
        初始化函数调用链可视化器
        
        Args:
            json_file_path: JSON文件的绝对路径
            display_type: 名称显示类型 ('english', 'chinese', 'both')
            output_format: 输出格式 ('mdd', 'graph')
        """
        self.json_file_path = json_file_path
        self.display_type = display_type
        self.output_format = output_format
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.calls: List[Dict[str, Any]] = []
        self._validate_inputs()
    
    def _validate_inputs(self) -> None:
        """验证输入参数"""
        # 验证display_type
        valid_display_types = ['english', 'chinese', 'both']
        if self.display_type not in valid_display_types:
            raise ValueError(f"无效的display_type: {self.display_type}。有效值为: {valid_display_types}")
        
        # 验证output_format
        valid_output_formats = ['mdd', 'graph']
        if self.output_format not in valid_output_formats:
            raise ValueError(f"无效的output_format: {self.output_format}。有效值为: {valid_output_formats}")
        
        # 验证文件存在
        if not os.path.exists(self.json_file_path):
            raise FileNotFoundError(f"JSON文件不存在: {self.json_file_path}")
        
        # 验证文件是绝对路径
        if not os.path.isabs(self.json_file_path):
            raise ValueError(f"json_file_path必须是绝对路径: {self.json_file_path}")
    
    def _load_json_data(self) -> None:
        """加载并解析JSON数据"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON文件格式错误: {e}")
        
        # 验证JSON结构
        if 'functions' not in data:
            raise ValueError("JSON文件缺少'functions'字段")
        
        if 'calls' not in data:
            raise ValueError("JSON文件缺少'calls'字段")
        
        # 处理函数数据
        for func in data['functions']:
            if 'id' not in func:
                raise ValueError("函数缺少'id'字段")
            if 'name' not in func:
                raise ValueError(f"函数 {func.get('id', 'unknown')} 缺少'name'字段")
            
            self.functions[func['id']] = {
                'id': func['id'],
                'name': func['name'],
                'chinese_name': func.get('chinese_name', ''),
                'description': func.get('description', ''),
                'module': func.get('module', ''),
                'file_path': func.get('file_path', '')
            }
        
        # 处理调用关系
        for call in data['calls']:
            if 'from' not in call:
                raise ValueError("调用关系缺少'from'字段")
            if 'to' not in call:
                raise ValueError("调用关系缺少'to'字段")
            
            # 验证调用的函数ID是否存在
            if call['from'] not in self.functions:
                raise ValueError(f"调用关系中的'from'函数ID不存在: {call['from']}")
            if call['to'] not in self.functions:
                raise ValueError(f"调用关系中的'to'函数ID不存在: {call['to']}")
            
            self.calls.append({
                'from': call['from'],
                'to': call['to'],
                'call_count': call.get('call_count', 1),
                'line_number': call.get('line_number', None)
            })
    
    def _get_display_name(self, func_id: str) -> str:
        """
        根据display_type获取函数的显示名称
        
        Args:
            func_id: 函数ID
            
        Returns:
            函数的显示名称
        """
        func = self.functions[func_id]
        english_name = func['name']
        chinese_name = func.get('chinese_name', '')
        
        if self.display_type == 'english':
            return english_name
        elif self.display_type == 'chinese':
            return chinese_name if chinese_name else english_name
        elif self.display_type == 'both':
            if chinese_name:
                return f"{english_name} ({chinese_name})"
            else:
                return english_name
        else:
            return english_name
    
    def _generate_mdd_output(self) -> str:
        """
        生成MDD格式的输出
        
        Returns:
            MDD格式的字符串
        """
        output = []
        
        # 标题
        output.append("# 函数调用链可视化")
        output.append("")
        
        # 概览
        output.append("## 概览")
        output.append("")
        output.append(f"总函数数：{len(self.functions)}")
        output.append(f"总调用数：{len(self.calls)}")
        output.append("")
        
        # 函数列表
        output.append("## 函数列表")
        output.append("")
        output.append("| ID | 名称 | 模块 | 描述 |")
        output.append("|----|------|------|------|")
        
        for func_id, func in self.functions.items():
            display_name = self._get_display_name(func_id)
            module = func.get('module', '')
            description = func.get('description', '')
            output.append(f"| {func_id} | {display_name} | {module} | {description} |")
        
        output.append("")
        
        # 调用链图
        output.append("## 调用链图")
        output.append("")
        output.append("```mermaid")
        output.append("flowchart TD")
        
        # 生成节点
        node_map = {}
        for i, func_id in enumerate(self.functions.keys()):
            node_id = chr(ord('A') + i)
            node_map[func_id] = node_id
            display_name = self._get_display_name(func_id)
            # 替换括号内的空格为<br/>以适应Mermaid
            mermaid_name = display_name.replace(' (', '<br/>(')
            output.append(f"    {node_id}[{mermaid_name}]")
        
        # 生成边
        for call in self.calls:
            from_node = node_map[call['from']]
            to_node = node_map[call['to']]
            output.append(f"    {from_node} --> {to_node}")
        
        output.append("```")
        output.append("")
        
        # 调用详情
        output.append("## 调用详情")
        output.append("")
        
        # 按调用者分组
        calls_by_caller = {}
        for call in self.calls:
            caller_id = call['from']
            if caller_id not in calls_by_caller:
                calls_by_caller[caller_id] = []
            calls_by_caller[caller_id].append(call)
        
        for caller_id, calls in calls_by_caller.items():
            caller_name = self._get_display_name(caller_id)
            output.append(f"### {caller_name} 调用：")
            
            for call in calls:
                callee_name = self._get_display_name(call['to'])
                call_count = call.get('call_count', 1)
                line_number = call.get('line_number', None)
                
                call_info = f"- {callee_name} ({call_count}次"
                if line_number:
                    call_info += f"，第{line_number}行"
                call_info += ")"
                output.append(call_info)
            
            output.append("")
        
        return "\n".join(output)
    
    def _generate_graph_output(self) -> str:
        """
        生成Graph格式的输出
        
        Returns:
            Graph格式的JSON字符串
        """
        nodes = []
        edges = []
        
        # 生成节点
        for func_id, func in self.functions.items():
            display_name = self._get_display_name(func_id)
            # 对于Graph格式，使用换行符分隔中英文
            if self.display_type == 'both' and func.get('chinese_name'):
                label = f"{func['name']}\n({func['chinese_name']})"
            else:
                label = display_name
            
            nodes.append({
                'id': func_id,
                'label': label,
                'properties': {
                    'name': func['name'],
                    'chinese_name': func.get('chinese_name', ''),
                    'module': func.get('module', ''),
                    'description': func.get('description', ''),
                    'file_path': func.get('file_path', '')
                }
            })
        
        # 生成边
        for i, call in enumerate(self.calls):
            edges.append({
                'id': f"edge{i+1}",
                'source': call['from'],
                'target': call['to'],
                'properties': {
                    'call_count': call.get('call_count', 1),
                    'line_number': call.get('line_number', None)
                }
            })
        
        # 生成元数据
        metadata = {
            'total_functions': len(self.functions),
            'total_calls': len(self.calls),
            'display_type': self.display_type,
            'generated_at': datetime.now().isoformat()
        }
        
        # 组合成最终的JSON
        result = {
            'nodes': nodes,
            'edges': edges,
            'metadata': metadata
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def visualize(self) -> str:
        """
        执行可视化，生成输出
        
        Returns:
            可视化结果字符串
        """
        # 加载JSON数据
        self._load_json_data()
        
        # 根据输出格式生成结果
        if self.output_format == 'mdd':
            return self._generate_mdd_output()
        elif self.output_format == 'graph':
            return self._generate_graph_output()
        else:
            raise ValueError(f"不支持的输出格式: {self.output_format}")


def main():
    """
    主函数，用于命令行调用
    
    使用方法:
    python function_call_chain_visualizer.py <json_file_path> <display_type> <output_format>
    
    示例:
    python function_call_chain_visualizer.py /path/to/call_chain.json both mdd
    """
    if len(sys.argv) != 4:
        print("使用方法: python function_call_chain_visualizer.py <json_file_path> <display_type> <output_format>")
        print("示例: python function_call_chain_visualizer.py /path/to/call_chain.json both mdd")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    display_type = sys.argv[2]
    output_format = sys.argv[3]
    
    try:
        visualizer = FunctionCallChainVisualizer(json_file_path, display_type, output_format)
        result = visualizer.visualize()
        print(result)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
