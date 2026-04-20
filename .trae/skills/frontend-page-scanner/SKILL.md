---
name: "frontend-page-scanner"
description: "扫描前端TSX页面中的按钮、表单和交互流程，构建操作链用于E2E测试用例生成。当用户需要分析前端页面交互、识别按钮和表单、或构建操作流程时调用此skill。"
---

# 前端页面扫描工具 (Frontend Page Scanner)

本skill用于扫描前端TSX页面代码，识别按钮、表单、向导等交互元素，构建操作链用于E2E测试用例生成。

## 何时调用

在以下情况应该自动调用此skill：
- 用户需要分析前端页面的交互元素
- 用户想要识别页面中的按钮和表单
- 用户需要构建操作流程/操作链
- 用户询问E2E测试用例生成的前置分析
- 用户需要可视化前端页面的交互流程

## 项目位置

代码位于项目根目录的 `frontend_page_scanner/` 文件夹中：

```
display-skill/
├── frontend_page_scanner/           # 主代码包
│   ├── __init__.py
│   ├── main.py                       # 主入口
│   ├── models/
│   │   ├── __init__.py
│   │   └── data_models.py            # 数据模型定义
│   ├── scanners/
│   │   ├── __init__.py
│   │   ├── button_scanner.py         # 按钮扫描器
│   │   ├── form_scanner.py           # 表单扫描器
│   │   ├── step_scanner.py           # 步骤/向导扫描器
│   │   └── api_call_scanner.py       # API调用扫描器
│   ├── builders/
│   │   ├── __init__.py
│   │   └── operation_chain_builder.py # 操作链构建器
│   └── utils/
│       ├── __init__.py
│       └── helpers.py                # 辅助函数
└── frontend_interaction_viewer.html  # 交互流程可视化页面
```

## 功能概述

### 1. 按钮识别 (Button Scanner)

识别 Ant Design 按钮组件及其交互事件：

**识别模式：**
```tsx
// 标准按钮
<Button type="primary" onClick={handleNext}>下一步</Button>
<Button onClick={handleCancel}>取消</Button>
<Button type="primary" onClick={handleFinish}>创建</Button>

// 带图标的按钮
<Button type="primary" icon={<PlusOutlined />}>新增</Button>

// 危险按钮
<Button danger onClick={handleDelete}>删除</Button>
```

**识别的按钮类型：**
- `primary` - 主要按钮（下一步、创建、确认等）
- `default` - 默认按钮（取消、关闭等）
- `danger` - 危险按钮（删除等）
- `link` - 链接按钮

### 2. 表单识别 (Form Scanner)

识别 Ant Design 表单组件及其字段：

**识别模式：**
```tsx
<Form form={form} layout="vertical">
  <Form.Item name="name" label="名称" rules={[{ required: true }]}>
    <Input placeholder="请输入名称" />
  </Form.Item>
  <Form.Item name="region" label="区域">
    <Select>
      <Option value="cn-beijing">北京</Option>
    </Select>
  </Form.Item>
</Form>
```

**识别的表单项类型：**
- `Input` - 文本输入
- `Input.Password` - 密码输入
- `Input.TextArea` - 多行文本
- `Select` - 下拉选择
- `Cascader` - 级联选择
- `Switch` - 开关
- `Radio.Group` - 单选框组
- `Checkbox.Group` - 多选框组
- `DatePicker` / `RangePicker` - 日期选择
- `Upload` - 文件上传

### 3. 步骤/向导识别 (Step Scanner)

识别 Ant Design Steps 组件和向导模式：

**识别模式：**
```tsx
const steps = ['选择云平台', '配置云账号', '连接测试'];

<Steps current={currentStep}>
  <Step title="选择云平台" />
  <Step title="配置云账号" />
  <Step title="连接测试" />
</Steps>

// 步骤切换函数
const handleNext = () => { setCurrentStep(currentStep + 1); }
const handlePrev = () => { setCurrentStep(currentStep - 1); }
```

**识别的向导模式：**
- 标准步骤数组定义
- Steps 组件
- 步骤切换函数 (next, prev, handleNext, handlePrev)
- 当前步骤状态管理

### 4. API调用识别 (API Call Scanner)

识别前端 API 调用：

**识别模式：**
```tsx
// apiPost, apiRequest 等封装调用
await apiPost('/api/clouds', payload);
const response = await apiRequest('/api/clouds');

// axios 调用
await axios.post('/api/clouds', data);
await axios.get('/api/clouds');

// fetch 调用
await fetch('/api/clouds', { method: 'POST', body: JSON.stringify(data) });
```

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project_path` | string | 是 | 目标前端项目路径 |
| `scan_mode` | string | 是 | 扫描模式 |
| `output_format` | string | 是 | 输出格式 |

### 扫描模式 (scan_mode)

| 值 | 说明 |
|----|------|
| `full` | 完整扫描（按钮+表单+步骤+API） |
| `buttons` | 仅扫描按钮 |
| `forms` | 仅扫描表单 |
| `steps` | 仅扫描步骤/向导 |
| `api_calls` | 仅扫描API调用 |
| `operation_chains` | 仅构建操作链 |

### 输出格式 (output_format)

| 值 | 说明 |
|----|------|
| `json` | 输出JSON格式 |
| `visualizer` | 生成可视化页面 |
| `both` | 同时输出JSON和可视化 |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `include_patterns` | array | `["**/*.tsx"]` | 包含的文件模式 |
| `exclude_patterns` | array | `["node_modules/**", "dist/**"]` | 排除的文件模式 |
| `max_files` | number | 500 | 最大扫描文件数 |
| `output_dir` | string | 项目目录 | 输出目录 |

## 输出格式

### JSON 输出结构

```json
{
  "skill_version": "1.0",
  "scan_type": "frontend_interaction",
  "summary": {
    "total_files_scanned": 45,
    "total_buttons": 120,
    "total_forms": 35,
    "total_steps": 15,
    "total_api_calls": 85,
    "total_operation_chains": 25
  },
  "buttons": [
    {
      "id": "btn_001",
      "name": "下一步",
      "type": "primary",
      "action_type": "next_step",
      "onClick": "handleNext",
      "file_path": "/frontend/src/pages/Clouds/CloudWizard.tsx",
      "location": { "start_line": 898, "end_line": 900 },
      "icon": "PlusOutlined",
      "text_content": "下一步",
      "container_type": "wizard"
    }
  ],
  "forms": [
    {
      "id": "form_001",
      "name": "CloudWizardForm",
      "form_instance": "form",
      "file_path": "/frontend/src/pages/Clouds/CloudWizard.tsx",
      "location": { "start_line": 544, "end_line": 732 },
      "fields": [
        {
          "name": "name",
          "label": "名称",
          "type": "input",
          "required": true,
          "rules": [{ "required": true, "message": "请输入名称" }],
          "location": { "start_line": 551, "end_line": 560 }
        }
      ],
      "validation_methods": ["form.validateFields"],
      "submit_methods": ["handleFinish"]
    }
  ],
  "steps": [
    {
      "id": "step_001",
      "wizard_name": "CloudWizard",
      "step_index": 0,
      "title": "选择云平台",
      "file_path": "/frontend/src/pages/Clouds/CloudWizard.tsx",
      "location": { "start_line": 124, "end_line": 124 },
      "next_step": 1,
      "prev_step": null,
      "buttons_in_step": ["handleProviderSelect"],
      "form_fields_in_step": []
    }
  ],
  "api_calls": [
    {
      "id": "api_001",
      "method": "POST",
      "path": "/api/clouds",
      "call_type": "apiPost",
      "file_path": "/frontend/src/pages/Clouds/CloudWizard.tsx",
      "location": { "start_line": 372, "end_line": 372 },
      "called_from": "handleFinish",
      "payload_construction": {
        "fields": ["name", "type", "region", "endpoint", "accessKey", "secretKey"]
      }
    }
  ],
  "operation_chains": [
    {
      "id": "chain_001",
      "name": "云资源创建流程",
      "file_path": "/frontend/src/pages/Clouds/CloudWizard.tsx",
      "steps": [
        {
          "step_order": 1,
          "type": "button_click",
          "button": { "id": "btn_001", "name": "选择云平台", "action": "handleProviderSelect" },
          "description": "用户点击选择某个云平台卡片"
        },
        {
          "step_order": 2,
          "type": "form_fill",
          "form": { "id": "form_001", "name": "CloudWizardForm" },
          "fields": ["type", "name", "region", "endpoint", "apiToken"],
          "description": "填写云账号配置信息"
        },
        {
          "step_order": 3,
          "type": "button_click",
          "button": { "id": "btn_002", "name": "下一步", "action": "handleNext" },
          "description": "点击下一步进入连接测试"
        },
        {
          "step_order": 4,
          "type": "form_validate",
          "form": { "id": "form_001" },
          "description": "表单验证"
        },
        {
          "step_order": 5,
          "type": "api_call",
          "api_call": { "id": "api_001", "method": "POST", "path": "/api/clouds/test-connection" },
          "description": "调用连接测试API"
        },
        {
          "step_order": 6,
          "type": "button_click",
          "button": { "id": "btn_003", "name": "完成", "action": "handleFinish" },
          "description": "点击完成创建资源"
        },
        {
          "step_order": 7,
          "type": "api_call",
          "api_call": { "id": "api_002", "method": "POST", "path": "/api/clouds" },
          "description": "调用创建云资源API"
        }
      ],
      "metadata": {
        "total_steps": 7,
        "button_clicks": 3,
        "form_fills": 1,
        "api_calls": 2,
        "page_name": "CloudWizard"
      }
    }
  ],
  "output_files": {
    "json": "/output/frontend_interaction_result.json",
    "visualizer": "/output/frontend_interaction_viewer.html"
  }
}
```

## 操作链构建规则

### 按钮 → 表单 → API 的关联

1. **按钮点击事件分析**：
   - 识别 `onClick` 绑定的处理函数
   - 分析处理函数内部逻辑

2. **处理函数行为分析**：
   - 调用 `form.validateFields()` → 表单验证
   - 调用 `form.getFieldsValue()` → 表单提交
   - 调用 `setCurrentStep()` → 步骤切换
   - 调用 `apiPost()`, `axios.post()` 等 → API调用

3. **操作链构建规则**：
   ```
   按钮点击 → [步骤切换] → [表单填写] → [表单验证] → API调用
   ```

### 关键按钮识别

| 按钮文本 | 推测行为 |
|----------|----------|
| 新增/添加/创建 | 打开创建表单/模态框 |
| 编辑/修改 | 打开编辑表单 |
| 删除/移除 | 确认删除对话框 |
| 下一步/下一页 | 步骤切换（前进） |
| 上一步/上一页 | 步骤切换（后退） |
| 完成/提交/确认 | 最终提交 |
| 取消/关闭 | 取消操作 |
| 测试/连接测试 | 测试连接 |
| 保存 | 保存配置 |

### 关键表单字段识别

| 字段名/Label | 推测用途 |
|--------------|----------|
| name/名称/名字 | 资源名称 |
| type/类型 | 资源类型 |
| region/区域/地域 | 区域选择 |
| endpoint/端点/地址 | API端点 |
| accessKey/accessKeyId/密钥ID | 访问密钥ID |
| secretKey/secretAccessKey/密钥 | 访问密钥 |
| password/密码 | 密码 |
| username/用户名 | 用户名 |
| description/描述 | 描述信息 |

## 调用方式

### Python 模块导入

```python
import sys
from pathlib import Path

project_path = Path("/path/to/display-skill")
sys.path.insert(0, str(project_path))

from frontend_page_scanner.main import FrontendPageScanner

# 创建实例
scanner = FrontendPageScanner()

# 执行完整扫描
result = scanner.scan(
    project_path="/home/ws8634/programe/Compute.Tower-main",
    scan_mode="full",
    output_format="both",
    output_dir="/path/to/output"
)

if result["success"]:
    print(f"扫描完成！")
    print(f"按钮数: {result['summary']['total_buttons']}")
    print(f"表单数: {result['summary']['total_forms']}")
    print(f"操作链: {result['summary']['total_operation_chains']}")
    print(f"输出文件: {result['output_files']}")
else:
    print(f"扫描失败: {result['error']}")

# 仅扫描按钮
buttons_result = scanner.scan(
    project_path="/home/ws8634/programe/Compute.Tower-main",
    scan_mode="buttons",
    output_format="json"
)

# 仅构建操作链
chains_result = scanner.scan(
    project_path="/home/ws8634/programe/Compute.Tower-main",
    scan_mode="operation_chains",
    output_format="json"
)
```

### 命令行调用

```bash
# 进入项目目录
cd /path/to/display-skill

# 完整扫描
python -m frontend_page_scanner.main \
  --project-path /home/ws8634/programe/Compute.Tower-main \
  --scan-mode full \
  --output-format both

# 仅扫描按钮
python -m frontend_page_scanner.main \
  --project-path /home/ws8634/programe/Compute.Tower-main \
  --scan-mode buttons

# 仅构建操作链
python -m frontend_page_scanner.main \
  --project-path /home/ws8634/programe/Compute.Tower-main \
  --scan-mode operation_chains \
  --output-dir ./output

# 自定义文件模式
python -m frontend_page_scanner.main \
  --project-path /home/ws8634/programe/Compute.Tower-main \
  --scan-mode full \
  --include "**/pages/**/*.tsx" \
  --exclude "**/node_modules/**" "**/dist/**"
```

## 可视化页面

扫描完成后，可打开生成的 `frontend_interaction_viewer.html` 页面查看：

1. **按钮列表**：所有识别到的按钮及其属性
2. **表单详情**：表单结构和字段
3. **步骤向导**：向导流程可视化
4. **操作链图谱**：完整的交互流程图谱（使用 Cytoscape.js）
5. **API调用**：前端→后端API调用映射

## 与其他技能的关系

- **上游**：`code_analysis_skill` - 基础代码分析
- **下游**：`e2e_test_generator_skill` - 基于操作链生成E2E测试用例
- **相关**：`function_call_visualizer` - 函数调用链可视化

## 支持的技术栈

| 技术 | 支持状态 |
|------|----------|
| React + TypeScript (TSX) | ✓ 完整支持 |
| Ant Design 组件库 | ✓ 完整支持 |
| Ant Design Pro | ✓ 部分支持 |
| MUI (Material-UI) | ✗ 暂不支持 |
| Vue + TypeScript | ✗ 暂不支持 |
