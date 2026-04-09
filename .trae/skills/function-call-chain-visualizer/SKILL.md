---
name: "function-call-chain-visualizer"
description: "可视化函数调用链数据。当用户需要展示函数调用关系、生成markdown格式的调用图、或创建知识图谱视图时调用此skill。"
---

# 函数调用链可视化器

## 功能概述

本skill用于从JSON文件中读取函数调用链数据，并将其以可视化的方式展示出来。支持两种输出格式：
1. **MDD格式**：生成Markdown兼容的格式，可直接在Markdown查看器中渲染
2. **Graph格式**：生成知识图谱结构，适合页面交互式展示

支持三种名称显示类型：
1. **英文函数名**：仅显示英文函数名
2. **中文翻译名称**：仅显示中文翻译名称（无中文时回退到英文）
3. **中英文都显示**：同时显示英文和中文名称

## 输入参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `json_file_path` | string | 是 | 包含函数调用链数据的JSON文件的绝对路径 |
| `display_type` | string | 是 | 名称显示类型：'english'（英文函数名）、'chinese'（中文翻译名称）或'both'（中英文都显示） |
| `output_format` | string | 是 | 输出格式：'mdd'（Markdown格式）或'graph'（知识图谱格式） |

## JSON数据结构要求

输入的JSON文件应包含以下结构：

```json
{
  "functions": [
    {
      "id": "func1",
      "name": "calculateTotal",
      "chinese_name": "计算总价",
      "description": "计算商品的总价格",
      "module": "order",
      "file_path": "/src/order/calculator.js"
    },
    {
      "id": "func2",
      "name": "getItemPrice",
      "chinese_name": "获取商品价格",
      "description": "获取单个商品的价格",
      "module": "product",
      "file_path": "/src/product/price.js"
    }
  ],
  "calls": [
    {
      "from": "func1",
      "to": "func2",
      "call_count": 3,
      "line_number": 45
    }
  ]
}
```

## 输出格式

### 1. MDD格式（Markdown显示）

生成Markdown兼容的格式，包含：
- **函数概览表**：列出所有函数及其详细信息
- **调用链图**：使用Mermaid语法的可视化流程图
- **详细调用信息**：显示调用关系、次数和位置

#### MDD输出示例

```markdown
# 函数调用链可视化

## 概览

总函数数：3
总调用数：4

## 函数列表

| ID | 名称 | 模块 | 描述 |
|----|------|------|------|
| func1 | calculateTotal (计算总价) | order | 计算商品的总价格 |
| func2 | getItemPrice (获取商品价格) | product | 获取单个商品的价格 |
| func3 | applyDiscount (应用折扣) | discount | 对总价应用折扣 |

## 调用链图

```mermaid
flowchart TD
    A[calculateTotal<br/>(计算总价)] --> B[getItemPrice<br/>(获取商品价格)]
    A --> C[applyDiscount<br/>(应用折扣)]
```

## 调用详情

### calculateTotal (计算总价) 调用：
- getItemPrice (获取商品价格) (3次，第45行)
- applyDiscount (应用折扣) (1次，第52行)
```

### 2. Graph格式（知识图谱/页面视图）

生成适合交互式知识图谱可视化的结构化格式，包含：
- **节点**：每个函数作为一个节点，包含属性
- **边**：调用关系，包含属性
- **元数据**：用于渲染的附加信息

#### Graph输出示例

```json
{
  "nodes": [
    {
      "id": "func1",
      "label": "calculateTotal\n(计算总价)",
      "properties": {
        "name": "calculateTotal",
        "chinese_name": "计算总价",
        "module": "order",
        "description": "计算商品的总价格",
        "file_path": "/src/order/calculator.js"
      }
    },
    {
      "id": "func2",
      "label": "getItemPrice\n(获取商品价格)",
      "properties": {
        "name": "getItemPrice",
        "chinese_name": "获取商品价格",
        "module": "product",
        "description": "获取单个商品的价格",
        "file_path": "/src/product/price.js"
      }
    }
  ],
  "edges": [
    {
      "id": "edge1",
      "source": "func1",
      "target": "func2",
      "properties": {
        "call_count": 3,
        "line_number": 45
      }
    }
  ],
  "metadata": {
    "total_functions": 2,
    "total_calls": 1,
    "display_type": "both",
    "generated_at": "2026-04-09T10:30:00Z"
  }
}
```

## 名称显示类型

### 1. 仅英文 ('english')
- 仅显示英文函数名
- 示例：`calculateTotal`

### 2. 仅中文 ('chinese')
- 仅显示中文翻译名称
- 示例：`计算总价`
- 注意：如果中文名称不可用，回退到英文名称

### 3. 中英文都显示 ('both')
- 同时显示英文和中文名称
- 示例：`calculateTotal (计算总价)`
- 格式：`{english_name} ({chinese_name})`

## Python实现代码

以下是实现此功能的Python代码，可直接使用：

```python
import json
import os
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
    import sys
    
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
```

## 调用执行流程

### 1. 作为Python模块导入使用

```python
from function_call_chain_visualizer import FunctionCallChainVisualizer

# 创建可视化器实例
visualizer = FunctionCallChainVisualizer(
    json_file_path="/path/to/call_chain.json",
    display_type="both",  # 可选: 'english', 'chinese', 'both'
    output_format="mdd"   # 可选: 'mdd', 'graph'
)

# 执行可视化，获取结果
result = visualizer.visualize()

# 输出结果
print(result)

# 或者保存到文件
with open("/path/to/output.md", "w", encoding="utf-8") as f:
    f.write(result)
```

### 2. 作为命令行工具使用

```bash
# 基本用法
python function_call_chain_visualizer.py <json_file_path> <display_type> <output_format>

# 示例1: 生成MDD格式，显示中英文名称
python function_call_chain_visualizer.py /path/to/call_chain.json both mdd

# 示例2: 生成Graph格式，仅显示英文名称
python function_call_chain_visualizer.py /path/to/call_chain.json english graph

# 示例3: 保存输出到文件
python function_call_chain_visualizer.py /path/to/call_chain.json both mdd > output.md
```

### 3. 在Agent中调用

当Agent需要使用此skill时，应按照以下步骤执行：

1. **获取输入参数**：
   - `json_file_path`: JSON文件的绝对路径
   - `display_type`: 名称显示类型
   - `output_format`: 输出格式

2. **验证参数**：
   - 确保`json_file_path`是绝对路径且文件存在
   - 确保`display_type`是'english'、'chinese'或'both'之一
   - 确保`output_format`是'mdd'或'graph'之一

3. **执行可视化**：
   - 导入`FunctionCallChainVisualizer`类
   - 创建实例并调用`visualize()`方法
   - 处理可能的异常

4. **返回结果**：
   - 对于'mdd'格式，返回Markdown字符串
   - 对于'graph'格式，返回JSON字符串
   - 可以选择保存到文件或直接返回给用户

### 4. 完整调用示例

```python
# 完整示例：生成MDD格式并保存到文件
from function_call_chain_visualizer import FunctionCallChainVisualizer
import os

def visualize_call_chain(json_file_path, display_type, output_format, output_file=None):
    """
    可视化函数调用链
    
    Args:
        json_file_path: JSON文件的绝对路径
        display_type: 名称显示类型
        output_format: 输出格式
        output_file: 可选，输出文件路径
    
    Returns:
        可视化结果
    """
    try:
        # 创建可视化器
        visualizer = FunctionCallChainVisualizer(
            json_file_path=json_file_path,
            display_type=display_type,
            output_format=output_format
        )
        
        # 执行可视化
        result = visualizer.visualize()
        
        # 保存到文件（如果指定）
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"结果已保存到: {output_file}")
        
        return result
    
    except FileNotFoundError as e:
        print(f"文件未找到错误: {e}")
        return None
    except ValueError as e:
        print(f"参数错误: {e}")
        return None
    except Exception as e:
        print(f"未知错误: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    # 示例1: 生成MDD格式
    result1 = visualize_call_chain(
        json_file_path="/path/to/call_chain.json",
        display_type="both",
        output_format="mdd",
        output_file="/path/to/output.md"
    )
    
    # 示例2: 生成Graph格式
    result2 = visualize_call_chain(
        json_file_path="/path/to/call_chain.json",
        display_type="english",
        output_format="graph",
        output_file="/path/to/output.json"
    )
```

## 最佳实践

1. **可读性优先**：始终优先考虑人类可读性。使用清晰的格式、一致的间距和描述性标签。

2. **优雅处理缺失数据**：
   - 如果中文名称缺失，回退到英文名称
   - 如果调用次数缺失，假设为1
   - 如果行号缺失，从显示中省略

3. **一致的格式**：
   - 使用一致的缩进
   - 遵循Markdown表格和代码块的最佳实践
   - 使用有意义的节标题

4. **统计洞察**：
   - 包含函数和调用的总数
   - 突出显示最常调用的函数（如果适用）
   - 按模块分组以获得更好的组织

5. **错误处理**：
   - 在处理前验证JSON结构
   - 为无效输入提供清晰的错误消息
   - 优雅处理文件读取错误

## 注意事项

- 此skill设计用于可读性，而非针对非常大的数据集进行性能优化
- MDD格式中的Mermaid图与大多数支持Mermaid的Markdown查看器兼容
- Graph格式的输出可以直接与各种图可视化库一起使用
- 始终使用绝对路径作为JSON文件输入，以避免路径解析问题
- 确保Python环境中安装了必要的依赖（此实现仅使用标准库，无需额外依赖）
