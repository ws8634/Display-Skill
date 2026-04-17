#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
函数调用链可视化工具 (Function Call Visualizer)
用于读取函数调用链JSON数据，生成MDD图表或知识图谱数据。

支持两种输入格式：
1. nodes + edges 格式：原始代码分析结果
2. call_chains 格式：前端组件→后端API调用链
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .models.data_models import DisplayMode, OutputType
from .parsers.data_parser import UnifiedParser, DataValidator
from .generators.mdd_generator import MDDGenerator, CompactMDDGenerator, APICallMDDGenerator
from .generators.knowledge_graph_generator import KnowledgeGraphGenerator, EnhancedKnowledgeGraphGenerator


class FunctionCallVisualizer:
    
    def __init__(self):
        pass
    
    def visualize(self,
                  json_file: str,
                  display_mode: str = "english",
                  output_type: str = "mdd",
                  compact: bool = False,
                  enhanced: bool = False,
                  api_only: bool = False) -> Dict[str, Any]:
        try:
            display_mode_enum = self._parse_display_mode(display_mode)
            output_type_enum = self._parse_output_type(output_type)
            
            graph_data = UnifiedParser.parse_file(json_file)
            
            result = {
                "success": True,
                "input_file": json_file,
                "display_mode": display_mode,
                "output_type": output_type,
                "source_format": graph_data.source_format,
                "statistics": {}
            }
            
            if output_type_enum == OutputType.MDD:
                if api_only:
                    generator = APICallMDDGenerator(display_mode_enum)
                    mdd = generator.generate_api_calls(graph_data)
                    result["output"] = {
                        "type": "mdd",
                        "format": "mermaid",
                        "diagram": mdd,
                        "filter": "api_only"
                    }
                elif compact:
                    generator = CompactMDDGenerator(display_mode_enum)
                    diagrams = generator.generate_compact(graph_data)
                    result["output"] = {
                        "type": "mdd",
                        "format": "mermaid",
                        "diagrams": diagrams,
                        "diagram_count": len(diagrams)
                    }
                else:
                    generator = MDDGenerator(display_mode_enum)
                    mdd, stats = generator.generate_with_stats(graph_data)
                    result["output"] = {
                        "type": "mdd",
                        "format": "mermaid",
                        "diagram": mdd
                    }
                    result["statistics"] = stats
            
            else:
                if enhanced:
                    generator = EnhancedKnowledgeGraphGenerator(display_mode_enum)
                    graph_data_output = generator.generate_with_hierarchy(graph_data)
                else:
                    generator = KnowledgeGraphGenerator(display_mode_enum)
                    graph_data_output = generator.generate(graph_data)
                
                result["output"] = {
                    "type": "knowledge-graph",
                    "format": "json",
                    "data": graph_data_output
                }
                
                if "statistics" in graph_data_output:
                    result["statistics"] = graph_data_output["statistics"]
            
            if not result["statistics"]:
                from .utils.helpers import GraphAnalyzer
                result["statistics"] = GraphAnalyzer.generate_statistics(graph_data)
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }

    def validate(self, json_file: str) -> Dict[str, Any]:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            is_valid, errors = DataValidator.validate(data)
            
            format_type = "unknown"
            try:
                from .parsers.data_parser import FormatDetector
                format_type = FormatDetector.detect(data)
            except:
                pass
            
            return {
                "success": is_valid,
                "format_type": format_type,
                "errors": errors,
                "node_count": len(data.get("nodes", [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "errors": [f"文件读取或解析错误: {str(e)}"],
                "error_type": type(e).__name__
            }

    def _parse_display_mode(self, mode: str) -> DisplayMode:
        mode_lower = mode.lower()
        if mode_lower in ("english", "en"):
            return DisplayMode.ENGLISH
        elif mode_lower in ("chinese", "cn"):
            return DisplayMode.CHINESE
        elif mode_lower in ("both", "all"):
            return DisplayMode.BOTH
        else:
            return DisplayMode.ENGLISH

    def _parse_output_type(self, output_type: str) -> OutputType:
        type_lower = output_type.lower()
        if type_lower in ("mdd", "mermaid", "diagram"):
            return OutputType.MDD
        elif type_lower in ("knowledge-graph", "graph", "kg"):
            return OutputType.KNOWLEDGE_GRAPH
        else:
            return OutputType.MDD


def main():
    parser = argparse.ArgumentParser(
        description="函数调用链可视化工具 - 读取JSON数据，生成MDD图表或知识图谱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
支持的数据格式:

1. Nodes + Edges 格式（代码分析结果）:
{
  "nodes": [
    {"id": "n1", "type": "Function", "name": "myFunc", ...},
    {"id": "n2", "type": "API", "name": "createUser", "method": "POST", "path": "/api/users", ...}
  ],
  "edges": [
    {"source": "n1", "target": "n2", "type": "CALLS", "call_type": "api_call", ...}
  ]
}

2. Call Chains 格式（前端→后端API调用）:
[
  {
    "source_component": "UserForm",
    "source_chinese": "用户表单组件",
    "target_api": "createUser",
    "target_chinese": "创建用户",
    "method": "POST",
    "path": "/api/users",
    ...
  }
]

示例用法:
  # 验证JSON格式
  python -m function_call_visualizer --json-file data.json --validate
  
  # 生成MDD图表（英文）
  python -m function_call_visualizer --json-file data.json --display-mode english --output-type mdd
  
  # 生成MDD图表（中英文）并保存
  python -m function_call_visualizer --json-file data.json -d both -t mdd -o result.mmd
  
  # 生成知识图谱（美化JSON）
  python -m function_call_visualizer --json-file data.json -d chinese -t knowledge-graph --pretty
  
  # 仅显示API调用
  python -m function_call_visualizer --json-file data.json -t mdd --api-only
  
  # 大型数据使用紧凑模式
  python -m function_call_visualizer --json-file large_data.json -t mdd --compact
        """
    )
    
    parser.add_argument(
        "--json-file", "-f",
        required=True,
        help="JSON数据文件的路径"
    )
    
    parser.add_argument(
        "--display-mode", "-d",
        choices=["english", "chinese", "both", "en", "cn", "all"],
        default="english",
        help="名称显示模式: english(英文), chinese(中文), both(中英文)"
    )
    
    parser.add_argument(
        "--output-type", "-t",
        choices=["mdd", "knowledge-graph", "graph", "mermaid", "kg"],
        default="mdd",
        help="输出类型: mdd(Mermaid图表), knowledge-graph(知识图谱JSON)"
    )
    
    parser.add_argument(
        "--output-file", "-o",
        help="输出文件路径（不指定则输出到标准输出）"
    )
    
    parser.add_argument(
        "--compact", "-c",
        action="store_true",
        help="紧凑模式（适用于大型调用链，自动分割）"
    )
    
    parser.add_argument(
        "--enhanced", "-e",
        action="store_true",
        help="增强模式（知识图谱包含层次结构和分层信息）"
    )
    
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="仅显示API调用（前端组件→后端API）"
    )
    
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="仅验证JSON格式，不生成输出"
    )
    
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="美化JSON输出（仅对knowledge-graph有效）"
    )
    
    args = parser.parse_args()
    
    visualizer = FunctionCallVisualizer()
    
    if args.validate:
        result = visualizer.validate(args.json_file)
        print(f"格式类型: {result['format_type']}")
        
        if result["success"]:
            print("✓ JSON格式验证通过！")
            print(f"节点数量: {result.get('node_count', 0)}")
        else:
            print("✗ JSON格式验证失败！")
            print("\n错误列表:")
            for error in result.get("errors", []):
                print(f"  - {error}")
            sys.exit(1)
        
        sys.exit(0)
    
    result = visualizer.visualize(
        json_file=args.json_file,
        display_mode=args.display_mode,
        output_type=args.output_type,
        compact=args.compact,
        enhanced=args.enhanced,
        api_only=args.api_only
    )
    
    if not result["success"]:
        print(f"错误: {result.get('error', '未知错误')}", file=sys.stderr)
        if result.get("error_type"):
            print(f"错误类型: {result['error_type']}", file=sys.stderr)
        if result.get("traceback"):
            print(f"\n详细信息:\n{result['traceback']}", file=sys.stderr)
        sys.exit(1)
    
    output_content = ""
    
    if result["output"]["type"] == "mdd":
        if "diagrams" in result["output"]:
            output_content = "\n\n".join([
                f"%% 图表 {i+1}/{result['output']['diagram_count']}\n{d}"
                for i, d in enumerate(result["output"]["diagrams"])
            ])
        else:
            output_content = result["output"]["diagram"]
        
        output_ext = "mmd"
    else:
        indent = 2 if args.pretty else None
        output_content = json.dumps(result["output"]["data"], ensure_ascii=False, indent=indent)
        output_ext = "json"
    
    if args.output_file:
        output_path = Path(args.output_file)
        if not output_path.suffix:
            output_path = output_path.with_suffix(f".{output_ext}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        print(f"✓ 输出已保存到: {output_path}")
        
        if result.get("statistics"):
            print("\n统计信息:")
            stats = result["statistics"]
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"  {key}: {value}")
    else:
        print(output_content)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
