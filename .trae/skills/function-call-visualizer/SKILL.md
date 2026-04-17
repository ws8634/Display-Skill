---
name: "function-call-visualizer"
description: "从JSON数据可视化函数调用链。当用户需要展示函数调用关系、生成MDD图表、或创建知识图谱数据用于函数调用分析时调用此skill。"
---

# 函数调用链可视化工具 (Function Call Visualizer)

本skill用于读取函数调用链JSON数据，将调用关系以可视化方式展示。

## 何时调用

在以下情况应该自动调用此skill：
- 用户有包含函数调用链数据的JSON文件
- 用户想要可视化函数依赖和调用关系
- 用户需要生成MDD图表用于快速Markdown显示
- 用户需要结构化数据用于知识图谱可视化
- 用户询问调用链分析、函数依赖映射或调用层次可视化

## 项目位置

代码位于项目根目录的 `function_call_visualizer/` 文件夹中（标准Python包结构）：

```
display-skill/
├── function_call_visualizer/      # 主代码包（标准位置）
│   ├── __init__.py
│   ├── main.py                    # 主入口
│   ├── models/
│   │   ├── __init__.py
│   │   └── data_models.py         # 数据模型
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── data_parser.py         # 数据解析器
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── mdd_generator.py       # MDD生成器
│   │   └── knowledge_graph_generator.py  # 知识图谱生成器
│   └── utils/
│       ├── __init__.py
│       └── helpers.py             # 辅助函数
├── test_data_nodes_edges.json     # 测试数据1（nodes+edges格式）
└── test_data_call_chains.json     # 测试数据2（call_chains格式）
```

## 支持的输入格式

### 格式1：Nodes + Edges（代码分析结果）

```json
{
  "skill_version": "1.0",
  "analysis_type": "full",
  "nodes": [
    {
      "id": "node_001",
      "type": "Component",        // 或 "Function", "API"
      "name": "CloudWizard",
      "name_cn": "云资源创建向导",  // 可选：中文名称
      "file_path": "/frontend/src/pages/cloud/CloudWizard.tsx",
      "location": { "start_line": 45, "end_line": 280 },
      "signature": {
        "parameters": [],
        "is_async": false
      },
      "method": "POST",           // API特有：HTTP方法
      "path": "/api/clouds"       // API特有：路径
    }
  ],
  "edges": [
    {
      "id": "edge_001",
      "type": "CALLS",
      "call_type": "api_call",    // direct, cross_file, api_call
      "source": "node_001",
      "target": "node_002",
      "is_async": true
    }
  ]
}
```

### 格式2：Call Chains（前端→后端API调用）

```json
[
  {
    "source_component": "CloudWizard",
    "source_chinese": "云资源创建向导",
    "source_type": "Component",
    "target_api": "createCloud",
    "target_chinese": "创建云资源",
    "method": "POST",
    "path": "/api/clouds",
    "file_path": "/backend/src/routes/cloud.ts",
    "source_file": "/frontend/src/pages/cloud/CloudWizard.tsx"
  }
]
```

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `json_file` | string | 是 | JSON数据文件的绝对路径 |
| `display_mode` | string | 是 | 名称显示模式 |
| `output_type` | string | 是 | 输出格式 |

### 显示模式 (display_mode)

| 值 | 别名 | 说明 |
|----|------|------|
| `english` | `en` | 仅显示英文名称 |
| `chinese` | `cn` | 仅显示中文名称 |
| `both` | `all` | 中英文双语显示 |

### 输出格式 (output_type)

| 值 | 别名 | 说明 |
|----|------|------|
| `mdd` | `mermaid`, `diagram` | 生成Mermaid Diagram语法 |
| `knowledge-graph` | `graph`, `kg` | 生成结构化JSON数据 |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `compact` | boolean | false | 紧凑模式（大型数据自动分割） |
| `enhanced` | boolean | false | 增强模式（知识图谱额外信息） |
| `api_only` | boolean | false | 仅显示API调用关系 |

## 调用方式

### 方式1：Python模块导入

```python
import sys
from pathlib import Path

# 添加项目路径
project_path = Path("/path/to/display-skill")
sys.path.insert(0, str(project_path))

from function_call_visualizer.main import FunctionCallVisualizer

# 创建实例
visualizer = FunctionCallVisualizer()

# 1. 验证数据
validation = visualizer.validate("/path/to/data.json")
if validation["success"]:
    print(f"格式: {validation['format_type']}")
else:
    print(f"错误: {validation['errors']}")

# 2. 生成MDD
result = visualizer.visualize(
    json_file="/path/to/data.json",
    display_mode="both",        # english, chinese, both
    output_type="mdd"            # mdd, knowledge-graph
)

if result["success"]:
    mdd_code = result["output"]["diagram"]
    print("生成的MDD:")
    print(mdd_code)
    
    print("\n统计信息:")
    for k, v in result["statistics"].items():
        print(f"  {k}: {v}")
else:
    print(f"错误: {result['error']}")

# 3. 生成知识图谱
result = visualizer.visualize(
    json_file="/path/to/data.json",
    display_mode="chinese",
    output_type="knowledge-graph",
    enhanced=True               # 包含层次结构
)

if result["success"]:
    import json
    graph_data = result["output"]["data"]
    print(json.dumps(graph_data, ensure_ascii=False, indent=2))
```

### 方式2：命令行调用

```bash
# 进入项目目录
cd /path/to/display-skill

# 验证数据格式
python -m function_call_visualizer.main \
  --json-file test_data_nodes_edges.json \
  --validate

# 生成MDD（中英文显示）
python -m function_call_visualizer.main \
  --json-file test_data_nodes_edges.json \
  --display-mode both \
  --output-type mdd

# 仅显示API调用
python -m function_call_visualizer.main \
  --json-file test_data_call_chains.json \
  --output-type mdd \
  --api-only

# 生成知识图谱并美化输出
python -m function_call_visualizer.main \
  --json-file test_data_nodes_edges.json \
  --display-mode chinese \
  --output-type knowledge-graph \
  --pretty

# 保存到文件
python -m function_call_visualizer.main \
  --json-file test_data_nodes_edges.json \
  --output-type mdd \
  --output-file output.mmd
```

### 方式3：Agent自动调用流程

当用户请求可视化时，按以下步骤执行：

1. **参数确认**
   - JSON文件路径
   - 显示模式（默认 `both`）
   - 输出类型（根据用户意图选择）

2. **验证输入**
   ```python
   validation = visualizer.validate(json_file)
   if not validation["success"]:
       # 报告错误给用户
   ```

3. **执行生成**
   ```python
   result = visualizer.visualize(...)
   ```

4. **输出结果**
   - MDD：展示Mermaid代码块
   - 知识图谱：展示JSON或说明如何使用

## 输出示例

### MDD输出示例

```mermaid
flowchart TD
    classDef root fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1;
    classDef component fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20;
    classDef function fill:#f5f5f5,stroke:#757575,stroke-width:1px,color:#212121;
    classDef api fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100;

    subgraph frontend_src_pages_cloud [frontend/src/pages/cloud]
        CloudWizard[CloudWizard<br/>云资源创建向导]:::component
        CloudList[CloudList<br/>云资源列表]:::component
    end

    subgraph backend_src_routes [backend/src/routes]
        createCloud([createCloud<br/>创建云资源<br/>POST /api/clouds]):::api
        getCloudList([getCloudList<br/>获取云列表<br/>GET /api/clouds]):::api
        deleteCloud([deleteCloud<br/>删除云资源<br/>DELETE /api/clouds/:id]):::api
    end

    CloudWizard -->|API调用|POST| createCloud
    CloudList -->|API调用|GET| getCloudList
    CloudList -->|API调用|DELETE| deleteCloud
```

### 知识图谱输出结构

```json
{
  "graph": {
    "metadata": {
      "display_mode": "both",
      "source_format": "nodes_edges",
      "generated_at": "2024-01-15T10:30:00Z"
    },
    "nodes": [
      {
        "id": "CloudWizard",
        "label": "CloudWizard (云资源创建向导)",
        "type": "function",
        "subtype": "component",
        "file_path": "/frontend/src/pages/cloud/CloudWizard.tsx",
        "metadata": {
          "in_degree": 0,
          "out_degree": 1
        },
        "style": {
          "color": "#e8f5e9",
          "border_color": "#388e3c"
        }
      }
    ],
    "edges": [
      {
        "id": "edge_CloudWizard_to_createCloud",
        "source": "CloudWizard",
        "target": "createCloud",
        "type": "calls",
        "subtype": "api_call",
        "label": "API调用 | POST",
        "style": {
          "color": "#f57c00",
          "width": 2.0
        }
      }
    ],
    "modules": [...]
  },
  "statistics": {
    "total_nodes": 10,
    "total_edges": 8,
    "api_call_count": 4,
    "max_depth": 3
  }
}
```

## 核心特性

| 特性 | 说明 |
|------|------|
| **双格式支持** | 自动检测并处理 `nodes+edges` 和 `call_chains` 两种格式 |
| **三种显示模式** | 英文、中文、中英文双语 |
| **MDD生成** | 生成可直接渲染的Mermaid图表代码 |
| **知识图谱** | 生成结构化JSON，适用于D3.js、Cytoscape.js等 |
| **API调用过滤** | 可单独展示前端→后端API调用关系 |
| **循环依赖检测** | 自动检测并标记循环依赖 |
| **模块分组** | 按文件路径自动分组展示 |
| **详细统计** | 节点数、边数、最大深度、模块分布等 |

## 测试数据

项目中包含两个测试数据文件：

1. **`test_data_nodes_edges.json`** - nodes+edges格式示例
2. **`test_data_call_chains.json`** - call_chains格式示例

可用于验证功能是否正常。

## 相关技能

- `code_analysis_skill`: 从源代码生成 `nodes+edges` 格式数据
- `test_case_generator_skill`: 从 `edges` 中提取 `api_call` 构建业务流程
