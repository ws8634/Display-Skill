from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict

from ..models.data_models import (
    GraphData, Node, Edge, CallChain,
    NodeType, EdgeType, CallType, DisplayMode
)


class GraphAnalyzer:
    
    @staticmethod
    def detect_circular_dependencies(graph_data: GraphData) -> List[Tuple[str, str]]:
        node_ids = set(n.id for n in graph_data.nodes)
        
        adjacency = defaultdict(list)
        for edge in graph_data.edges:
            if edge.source and edge.target:
                adjacency[edge.source].append(edge.target)
        
        circular_pairs = []
        visited = set()
        recursion_stack = set()
        
        def dfs(node: str, path: List[str]):
            if node in recursion_stack:
                idx = path.index(node)
                cycle = path[idx:]
                if len(cycle) >= 2:
                    for i in range(len(cycle)):
                        for j in range(i + 1, len(cycle)):
                            pair = tuple(sorted([cycle[i], cycle[j]]))
                            if pair not in circular_pairs:
                                circular_pairs.append(pair)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            recursion_stack.add(node)
            path.append(node)
            
            for neighbor in adjacency[node]:
                dfs(neighbor, path)
            
            path.pop()
            recursion_stack.remove(node)
        
        for node_id in node_ids:
            if node_id not in visited:
                dfs(node_id, [])
        
        return circular_pairs

    @staticmethod
    def calculate_call_counts(graph_data: GraphData) -> Dict[Tuple[str, str], int]:
        call_counts = defaultdict(int)
        for edge in graph_data.edges:
            if edge.source and edge.target:
                key = (edge.source, edge.target)
                call_counts[key] += 1
        return dict(call_counts)

    @staticmethod
    def calculate_in_out_degrees(graph_data: GraphData) -> Dict[str, Tuple[int, int]]:
        in_degrees = defaultdict(int)
        out_degrees = defaultdict(int)
        
        for node in graph_data.nodes:
            in_degrees[node.id] = 0
            out_degrees[node.id] = 0
        
        for edge in graph_data.edges:
            if edge.source:
                out_degrees[edge.source] += 1
            if edge.target:
                in_degrees[edge.target] += 1
        
        result = {}
        for node in graph_data.nodes:
            result[node.id] = (in_degrees[node.id], out_degrees[node.id])
        
        return result

    @staticmethod
    def find_root_nodes(graph_data: GraphData) -> Set[str]:
        roots = set()
        
        if graph_data.source_format == "call_chains":
            for node in graph_data.nodes:
                if node.type in (NodeType.COMPONENT, NodeType.FUNCTION):
                    roots.add(node.id)
        else:
            degrees = GraphAnalyzer.calculate_in_out_degrees(graph_data)
            for node_id, (in_degree, out_degree) in degrees.items():
                if in_degree == 0 and out_degree > 0:
                    roots.add(node_id)
        
        api_nodes = set(n.id for n in graph_data.nodes if n.type == NodeType.API)
        roots = roots - api_nodes
        
        if not roots:
            for node in graph_data.nodes:
                if node.type != NodeType.API:
                    roots.add(node.id)
        
        return roots

    @staticmethod
    def calculate_max_depth(graph_data: GraphData) -> int:
        node_ids = set(n.id for n in graph_data.nodes)
        
        adjacency = defaultdict(list)
        for edge in graph_data.edges:
            if edge.source and edge.target:
                adjacency[edge.source].append(edge.target)
        
        roots = GraphAnalyzer.find_root_nodes(graph_data)
        max_depth = 0
        
        def dfs_depth(node: str, depth: int, visited: Set[str]):
            nonlocal max_depth
            if node in visited:
                return
            visited.add(node)
            max_depth = max(max_depth, depth)
            
            for neighbor in adjacency[node]:
                dfs_depth(neighbor, depth + 1, visited.copy())
        
        for root in roots:
            dfs_depth(root, 1, set())
        
        return max_depth

    @staticmethod
    def generate_statistics(graph_data: GraphData) -> Dict[str, Any]:
        stats = {}
        
        if graph_data.summary:
            stats.update(graph_data.summary)
        
        stats["total_nodes"] = len(graph_data.nodes)
        stats["total_edges"] = len(graph_data.edges)
        
        node_types = defaultdict(int)
        for node in graph_data.nodes:
            node_types[node.type.value] += 1
        stats["node_types"] = dict(node_types)
        
        edge_types = defaultdict(int)
        call_types = defaultdict(int)
        for edge in graph_data.edges:
            edge_types[edge.type.value] += 1
            if edge.call_type:
                call_types[edge.call_type.value] += 1
        stats["edge_types"] = dict(edge_types)
        if call_types:
            stats["call_types"] = dict(call_types)
        
        api_call_edges = [e for e in graph_data.edges if e.call_type == CallType.API_CALL]
        stats["api_call_count"] = len(api_call_edges)
        
        circular = GraphAnalyzer.detect_circular_dependencies(graph_data)
        stats["circular_dependencies"] = len(circular)
        
        max_depth = GraphAnalyzer.calculate_max_depth(graph_data)
        stats["max_depth"] = max_depth
        
        if graph_data.nodes:
            stats["avg_edges_per_node"] = round(len(graph_data.edges) / len(graph_data.nodes), 2)
        
        files = set()
        for node in graph_data.nodes:
            if node.file_path:
                files.add(node.file_path)
        stats["unique_files"] = len(files)
        
        modules = defaultdict(list)
        for node in graph_data.nodes:
            if node.module_name:
                modules[node.module_name].append(node.id)
            elif node.file_path:
                parts = node.file_path.replace('\\', '/').split('/')
                if len(parts) > 1:
                    module = parts[-2] if parts[-1].endswith(('.ts', '.tsx', '.js', '.jsx')) else parts[-1]
                    modules[module].append(node.id)
        stats["module_count"] = len(modules)
        stats["module_distribution"] = {k: len(v) for k, v in modules.items()}
        
        return stats

    @staticmethod
    def group_nodes_by_module(graph_data: GraphData) -> Dict[str, List[str]]:
        modules = defaultdict(list)
        
        for node in graph_data.nodes:
            module = "默认模块"
            
            if node.module_name:
                module = node.module_name
            elif node.file_path:
                path = node.file_path.replace('\\', '/')
                parts = path.split('/')
                if len(parts) >= 2:
                    if parts[-1].endswith(('.ts', '.tsx', '.js', '.jsx')):
                        if len(parts) >= 3:
                            module = '/'.join(parts[-3:-1])
                        else:
                            module = parts[-2]
                    else:
                        module = parts[-2] if len(parts) >= 2 else parts[-1]
            
            modules[module].append(node.id)
        
        return dict(modules)


class NameManager:
    
    @staticmethod
    def generate_node_id(name: str, existing_ids: Dict[str, str] = None) -> str:
        if existing_ids and name in existing_ids:
            return existing_ids[name]
        
        clean_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        if not clean_name or not clean_name[0].isalpha():
            clean_name = 'node_' + clean_name
        
        node_id = clean_name
        counter = 1
        
        if existing_ids:
            while node_id in existing_ids.values():
                node_id = f"{clean_name}_{counter}"
                counter += 1
        
        return node_id

    @staticmethod
    def generate_edge_id(source_id: str, target_id: str, index: int = 0) -> str:
        if index == 0:
            return f"edge_{source_id}_to_{target_id}"
        else:
            return f"edge_{source_id}_to_{target_id}_{index}"

    @staticmethod
    def sanitize_for_mermaid(text: str) -> str:
        replacements = {
            '[': '⟦',
            ']': '⟧',
            '(': '⟮',
            ')': '⟯',
            '{': '❴',
            '}': '❵',
            ';': '；',
            '&': '＆',
            '#': '＃',
            '%': '％',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text

    @staticmethod
    def truncate_label(label: str, max_length: int = 60) -> str:
        if len(label) <= max_length:
            return label
        
        parts = label.split('<br/>')
        if len(parts) > 1:
            truncated_parts = []
            current_length = 0
            
            for part in parts:
                if current_length + len(part) <= max_length:
                    truncated_parts.append(part)
                    current_length += len(part) + 5
                else:
                    break
            
            result = '<br/>'.join(truncated_parts)
            if len(truncated_parts) < len(parts):
                result += '...'
            return result
        
        return label[:max_length - 3] + '...'


class StyleManager:
    
    ROOT_STYLE = {
        'fill': '#e3f2fd',
        'stroke': '#1976d2',
        'stroke_width': '2px',
        'color': '#0d47a1'
    }
    
    COMPONENT_STYLE = {
        'fill': '#e8f5e9',
        'stroke': '#388e3c',
        'stroke_width': '2px',
        'color': '#1b5e20'
    }
    
    FUNCTION_STYLE = {
        'fill': '#f5f5f5',
        'stroke': '#757575',
        'stroke_width': '1px',
        'color': '#212121'
    }
    
    API_STYLE = {
        'fill': '#fff3e0',
        'stroke': '#f57c00',
        'stroke_width': '2px',
        'color': '#e65100'
    }
    
    MODULE_STYLE = {
        'fill': '#f3e5f5',
        'stroke': '#7b1fa2',
        'stroke_width': '1px',
        'color': '#4a148c'
    }
    
    UNKNOWN_STYLE = {
        'fill': '#eceff1',
        'stroke': '#546e7a',
        'stroke_width': '1px',
        'color': '#37474f'
    }
    
    MODULE_COLORS = [
        '#bbdefb', '#c8e6c9', '#fff9c4', '#ffccbc', '#f8bbd0',
        '#e1bee7', '#cfd8dc', '#b3e5fc', '#dcedc8', '#ffe0b2',
        '#ffcdd2', '#f48fb1', '#ce93d8', '#90a4ae', '#81d4fa',
        '#c5e1a5', '#fff59d', '#ffab91', '#f48fb1', '#ce93d8'
    ]
    
    @classmethod
    def get_style_for_node_type(cls, node_type: NodeType) -> Dict[str, str]:
        style_map = {
            NodeType.FUNCTION: cls.FUNCTION_STYLE,
            NodeType.COMPONENT: cls.COMPONENT_STYLE,
            NodeType.API: cls.API_STYLE,
            NodeType.MODULE: cls.MODULE_STYLE,
            NodeType.CLASS: cls.MODULE_STYLE,
            NodeType.UNKNOWN: cls.UNKNOWN_STYLE
        }
        return style_map.get(node_type, cls.FUNCTION_STYLE)

    @classmethod
    def get_style_for_node(cls, node: Node, is_root: bool = False) -> Dict[str, str]:
        if is_root:
            return cls.ROOT_STYLE
        return cls.get_style_for_node_type(node.type)

    @classmethod
    def get_mermaid_class_name(cls, node_type: NodeType, is_root: bool = False) -> str:
        if is_root:
            return "root"
        
        class_map = {
            NodeType.FUNCTION: "function",
            NodeType.COMPONENT: "component",
            NodeType.API: "api",
            NodeType.MODULE: "module",
            NodeType.CLASS: "class",
            NodeType.UNKNOWN: "unknown"
        }
        return class_map.get(node_type, "function")

    @classmethod
    def get_mermaid_class_def(cls, class_name: str, style: Dict[str, str]) -> str:
        return (f"classDef {class_name} fill:{style['fill']},"
                f"stroke:{style['stroke']},stroke-width:{style['stroke_width']},"
                f"color:{style['color']};")

    @classmethod
    def get_all_mermaid_class_defs(cls) -> List[str]:
        defs = []
        defs.append(cls.get_mermaid_class_def("root", cls.ROOT_STYLE))
        defs.append(cls.get_mermaid_class_def("component", cls.COMPONENT_STYLE))
        defs.append(cls.get_mermaid_class_def("function", cls.FUNCTION_STYLE))
        defs.append(cls.get_mermaid_class_def("api", cls.API_STYLE))
        defs.append(cls.get_mermaid_class_def("module", cls.MODULE_STYLE))
        defs.append(cls.get_mermaid_class_def("class", cls.MODULE_STYLE))
        defs.append(cls.get_mermaid_class_def("unknown", cls.UNKNOWN_STYLE))
        return defs

    @classmethod
    def get_module_color(cls, module_index: int) -> str:
        return cls.MODULE_COLORS[module_index % len(cls.MODULE_COLORS)]

    @classmethod
    def get_edge_style(cls, call_type: Optional[CallType]) -> Dict[str, Any]:
        styles = {
            CallType.DIRECT: {'color': '#9e9e9e', 'width': 1.5, 'dash_style': 'solid', 'arrow': '-->'},
            CallType.CROSS_FILE: {'color': '#78909c', 'width': 1.5, 'dash_style': 'solid', 'arrow': '-->'},
            CallType.API_CALL: {'color': '#f57c00', 'width': 2.0, 'dash_style': 'solid', 'arrow': '-->'},
            CallType.ASYNC: {'color': '#ff9800', 'width': 1.5, 'dash_style': 'dashed', 'arrow': '-.->'},
        }
        
        if call_type in styles:
            return styles[call_type]
        
        return {'color': '#9e9e9e', 'width': 1.5, 'dash_style': 'solid', 'arrow': '-->'}

    @classmethod
    def get_method_color(cls, method: str) -> str:
        method_colors = {
            'GET': '#4caf50',
            'POST': '#2196f3',
            'PUT': '#ff9800',
            'DELETE': '#f44336',
            'PATCH': '#9c27b0',
            'OPTIONS': '#607d8b',
            'HEAD': '#795548'
        }
        return method_colors.get(method.upper(), '#9e9e9e')
