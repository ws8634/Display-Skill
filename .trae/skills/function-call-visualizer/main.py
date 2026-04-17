#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
函数调用链可视化工具 (Function Call Visualizer)
用于读取函数调用链JSON数据，生成MDD图表或知识图谱数据。
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from models.data_models import (
    DataParser, DataValidator, DisplayMode, OutputType, CallChainData
)
from generators.mdd_generator import MDDGenerator, CompactMDDGenerator
from generators.knowledge_graph_generator import (
    KnowledgeGraphGenerator, EnhancedKnowledgeGraphGenerator
)
from utils.helpers import GraphAnalyzer


class FunctionCallVisualizer:
    
    def __init__(self):
        pass
    
    def visualize(self, 
                  json_file: str,
                  display_mode: str = "english",
                  output_type: str = "mdd",
                  compact: bool = False,
                  enhanced: bool = False) -> Dict[str, Any]:
        try:
            display_mode_enum = self._parse_display_mode(display_mode)
            output_type_enum = self._parse_output_type(output_type)
            
            call_chain_data = DataParser.load_from_json_file(json_file)
            
            result = {
                "success": True,
                "input_file": json_file,
                "display_mode": display_mode,
                "output_type": output_type,
                "statistics": GraphAnalyzer.generate_statistics(call_chain_data)
            }
            
            if output_type_enum == OutputType.MDD:
                if compact:
                    generator = CompactMDDGenerator(display_mode_enum)
                    diagrams = generator.generate_compact(call_chain_data)
                    result["output"] = {
                        "type": "mdd",
                        "format": "mermaid",
                        "diagrams": diagrams,
                        "diagram_count": len(diagrams)
                    }
                else:
                    generator = MDDGenerator(display_mode_enum)
                    mdd, stats = generator.generate_with_stats(call_chain_data)
                    result["output"] = {
                        "type": "mdd",
                        "format": "mermaid",
                        "diagram": mdd,
                        "statistics": stats
                    }
            
            else:
                if enhanced:
                    generator = EnhancedKnowledgeGraphGenerator(display_mode_enum)
                    graph_data = generator.generate_with_hierarchy(
                        call_chain_data,
                        project_name=call_chain_data.project_name,
                        language=call_chain_data.language
                    )
                else:
                    generator = KnowledgeGraphGenerator(display_mode_enum)
                    graph_data = generator.generate(
                        call_chain_data,
                        project_name=call_chain_data.project_name,
                        language=call_chain_data.language
                    )
                
                result["output"] = {
                    "type": "knowledge-graph",
                    "format": "json",
                    "data": graph_data
                }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _parse_display_mode(self, mode: str) -> DisplayMode:
        mode_lower = mode.lower()
        if mode_lower == "english" or mode_lower == "en":
            return DisplayMode.ENGLISH
        elif mode_lower == "chinese" or mode_lower == "cn":
            return DisplayMode.CHINESE
        elif mode_lower == "both" or mode_lower == "all":
            return DisplayMode.BOTH
        else:
            return DisplayMode.ENGLISH

    def _parse_output_type(self, output_type: str) -> OutputType:
        type_lower = output_type.lower()
        if type_lower == "mdd" or type_lower == "mermaid" or type_lower == "diagram":
            return OutputType.MDD
        elif type_lower == "knowledge-graph" or type_lower == "graph" or type_lower == "kg":
            return OutputType.KNOWLEDGE_GRAPH
        else:
            return OutputType.MDD

    def validate_json(self, json_file: str) -> Dict[str, Any]:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            errors = DataValidator.validate_json(data)
            
            return {
                "success": len(errors) == 0,
                "errors": errors,
                "warnings": []
            }
            
        except Exception as e:
            return {
                "success": False,
                "errors": [f"文件读取或解析错误: {str(e)}"],
                "error_type": type(e).__name__
            }


def main():
    parser = argparse.ArgumentParser(
        description="函数调用链可视化工具 - 读取JSON数据，生成MDD图表或知识图谱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 生成MDD图表（英文显示）
  python main.py --json-file call_chains.json --output-type mdd --display-mode english
  
  # 生成MDD图表（中英文显示）
  python main.py --json-file call_chains.json --output-type mdd --display-mode both
  
  # 生成知识图谱数据
  python main.py --json-file call_chains.json --output-type knowledge-graph --display-mode chinese
  
  # 验证JSON文件格式
  python main.py --json-file call_chains.json --validate
  
  # 输出到文件
  python main.py --json-file call_chains.json --output-type mdd --output-file result.mmd
        """
    )
    
    parser.add_argument(
        "--json-file", "-f",
        required=True,
        help="函数调用链JSON数据文件的路径"
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
        help="输出文件路径（如果不指定则输出到标准输出）"
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
        "--validate", "-v",
        action="store_true",
        help="仅验证JSON文件格式，不生成输出"
    )
    
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="美化JSON输出（仅对knowledge-graph有效）"
    )
    
    args = parser.parse_args()
    
    visualizer = FunctionCallVisualizer()
    
    if args.validate:
        result = visualizer.validate_json(args.json_file)
        if result["success"]:
            print("✓ JSON文件格式验证通过！")
            print("\n统计信息:")
            try:
                call_chain_data = DataParser.load_from_json_file(args.json_file)
                stats = GraphAnalyzer.generate_statistics(call_chain_data)
                for key, value in stats.items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k, v in value.items():
                            print(f"    {k}: {v}")
                    else:
                        print(f"  {key}: {value}")
            except:
                pass
            sys.exit(0)
        else:
            print("✗ JSON文件格式验证失败！")
            print("\n错误列表:")
            for error in result["errors"]:
                print(f"  - {error}")
            sys.exit(1)
    
    result = visualizer.visualize(
        json_file=args.json_file,
        display_mode=args.display_mode,
        output_type=args.output_type,
        compact=args.compact,
        enhanced=args.enhanced
    )
    
    if not result["success"]:
        print(f"错误: {result.get('error', '未知错误')}", file=sys.stderr)
        if result.get("error_type"):
            print(f"错误类型: {result['error_type']}", file=sys.stderr)
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
        
        if "statistics" in result:
            print("\n统计信息:")
            for key, value in result["statistics"].items():
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
