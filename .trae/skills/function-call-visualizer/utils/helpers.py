from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from models.data_models import CallChainData, CallEdge, FunctionInfo, DisplayMode


class GraphAnalyzer:
    
    @staticmethod
    def detect_circular_dependencies(call_chain_data: CallChainData) -> List[Tuple[str, str]]:
        all_funcs = call_chain_data.get_all_functions()
        edges = call_chain_data.get_all_edges()
        
        adjacency = defaultdict(list)
        for edge in edges:
            adjacency[edge.caller.name].append(edge.callee.name)
        
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
        
        for func_name in all_funcs:
            if func_name not in visited:
                dfs(func_name, [])
        
        return circular_pairs

    @staticmethod
    def calculate_call_counts(call_chain_data: CallChainData) -> Dict[Tuple[str, str], int]:
        call_counts = defaultdict(int)
        edges = call_chain_data.get_all_edges()
        
        for edge in edges:
            key = (edge.caller.name, edge.callee.name)
            call_counts[key] += edge.call_count
        
        return dict(call_counts)

    @staticmethod
    def calculate_in_out_degrees(call_chain_data: CallChainData) -> Dict[str, Tuple[int, int]]:
        in_degrees = defaultdict(int)
        out_degrees = defaultdict(int)
        
        all_funcs = call_chain_data.get_all_functions()
        for func_name in all_funcs:
            in_degrees[func_name] = 0
            out_degrees[func_name] = 0
        
        edges = call_chain_data.get_all_edges()
        for edge in edges:
            out_degrees[edge.caller.name] += 1
            in_degrees[edge.callee.name] += 1
        
        result = {}
        for func_name in all_funcs:
            result[func_name] = (in_degrees[func_name], out_degrees[func_name])
        
        return result

    @staticmethod
    def find_root_functions(call_chain_data: CallChainData) -> Set[str]:
        roots = set()
        
        for chain in call_chain_data.call_chains:
            roots.add(chain.root_function.name)
        
        degrees = GraphAnalyzer.calculate_in_out_degrees(call_chain_data)
        for func_name, (in_degree, out_degree) in degrees.items():
            if in_degree == 0 and out_degree > 0:
                roots.add(func_name)
        
        return roots

    @staticmethod
    def calculate_max_depth(call_chain_data: CallChainData) -> int:
        all_funcs = call_chain_data.get_all_functions()
        edges = call_chain_data.get_all_edges()
        
        adjacency = defaultdict(list)
        for edge in edges:
            adjacency[edge.caller.name].append(edge.callee.name)
        
        roots = GraphAnalyzer.find_root_functions(call_chain_data)
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
    def generate_statistics(call_chain_data: CallChainData) -> Dict[str, Any]:
        all_funcs = call_chain_data.get_all_functions()
        edges = call_chain_data.get_all_edges()
        modules = call_chain_data.get_modules()
        circular_pairs = GraphAnalyzer.detect_circular_dependencies(call_chain_data)
        roots = GraphAnalyzer.find_root_functions(call_chain_data)
        max_depth = GraphAnalyzer.calculate_max_depth(call_chain_data)
        
        total_edges = len(edges)
        total_funcs = len(all_funcs)
        
        return {
            "total_nodes": total_funcs,
            "total_edges": total_edges,
            "total_modules": len(modules),
            "root_functions": len(roots),
            "circular_dependencies": len(circular_pairs),
            "max_depth": max_depth,
            "avg_calls_per_function": round(total_edges / total_funcs, 2) if total_funcs > 0 else 0,
            "module_distribution": {k: len(v) for k, v in modules.items()},
            "root_function_names": list(roots)
        }


class NameManager:
    
    @staticmethod
    def generate_node_id(func_name: str, existing_ids: Dict[str, str]) -> str:
        if func_name in existing_ids:
            return existing_ids[func_name]
        
        clean_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in func_name)
        
        if not clean_name or not clean_name[0].isalpha():
            clean_name = 'node_' + clean_name
        
        node_id = clean_name
        counter = 1
        
        while node_id in existing_ids.values():
            node_id = f"{clean_name}_{counter}"
            counter += 1
        
        existing_ids[func_name] = node_id
        return node_id

    @staticmethod
    def generate_edge_id(source: str, target: str, index: int = 0) -> str:
        if index == 0:
            return f"edge_{source}_to_{target}"
        else:
            return f"edge_{source}_to_{target}_{index}"

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
    def truncate_label(label: str, max_length: int = 50) -> str:
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
            
            return '<br/>'.join(truncated_parts) + '...'
        
        return label[:max_length - 3] + '...'


class StyleManager:
    
    ROOT_STYLE = {
        'fill': '#e1f5fe',
        'stroke': '#0288d1',
        'stroke_width': '2px',
        'color': '#01579b'
    }
    
    FUNC_STYLE = {
        'fill': '#f5f5f5',
        'stroke': '#757575',
        'stroke_width': '1px',
        'color': '#212121'
    }
    
    LIB_STYLE = {
        'fill': '#fff3e0',
        'stroke': '#f57c00',
        'stroke_width': '1px',
        'color': '#e65100'
    }
    
    CLASS_STYLE = {
        'fill': '#f3e5f5',
        'stroke': '#7b1fa2',
        'stroke_width': '1px',
        'color': '#4a148c'
    }
    
    MODULE_COLORS = [
        '#bbdefb', '#c8e6c9', '#fff9c4', '#ffccbc', '#f8bbd0',
        '#e1bee7', '#cfd8dc', '#b3e5fc', '#dcedc8', '#ffe0b2',
        '#ffcdd2', '#f48fb1', '#ce93d8', '#90a4ae', '#81d4fa'
    ]
    
    @classmethod
    def get_style_for_function_type(cls, func_type: str) -> Dict[str, str]:
        style_map = {
            'root': cls.ROOT_STYLE,
            'regular': cls.FUNC_STYLE,
            'library': cls.LIB_STYLE,
            'class': cls.CLASS_STYLE
        }
        return style_map.get(func_type, cls.FUNC_STYLE)

    @classmethod
    def get_mermaid_class_def(cls, func_type: str) -> str:
        style = cls.get_style_for_function_type(func_type)
        return (f"classDef {func_type} fill:{style['fill']},"
                f"stroke:{style['stroke']},stroke-width:{style['stroke_width']},"
                f"color:{style['color']};")

    @classmethod
    def get_all_mermaid_class_defs(cls) -> List[str]:
        return [
            cls.get_mermaid_class_def('root'),
            cls.get_mermaid_class_def('func'),
            cls.get_mermaid_class_def('lib'),
            cls.get_mermaid_class_def('class')
        ]

    @classmethod
    def get_module_color(cls, module_index: int) -> str:
        return cls.MODULE_COLORS[module_index % len(cls.MODULE_COLORS)]

    @classmethod
    def get_edge_style(cls, call_type: str) -> Dict[str, Any]:
        styles = {
            'sync': {'color': '#9e9e9e', 'width': 1.5, 'dash_style': 'solid', 'arrow': '-->'},
            'async': {'color': '#ff9800', 'width': 1.5, 'dash_style': 'dashed', 'arrow': '-.->'},
            'conditional': {'color': '#2196f3', 'width': 1.0, 'dash_style': 'dotted', 'arrow': '-.->'},
            'loop': {'color': '#f44336', 'width': 1.5, 'dash_style': 'dashdot', 'arrow': '-..->'}
        }
        return styles.get(call_type, styles['sync'])
