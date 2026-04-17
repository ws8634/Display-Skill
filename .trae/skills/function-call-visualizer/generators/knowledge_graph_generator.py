from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
from datetime import datetime
from models.data_models import (
    CallChainData, CallEdge, FunctionInfo, DisplayMode, CallType, FunctionType
)
from utils.helpers import GraphAnalyzer, NameManager, StyleManager


class KnowledgeGraphGenerator:
    
    def __init__(self, display_mode: DisplayMode = DisplayMode.ENGLISH):
        self.display_mode = display_mode
        self.node_ids: Dict[str, str] = {}
        self.edge_ids: Dict[Tuple[str, str], str] = {}

    def generate(self, call_chain_data: CallChainData, 
                 project_name: Optional[str] = None,
                 language: Optional[str] = None) -> Dict[str, Any]:
        self.node_ids.clear()
        self.edge_ids.clear()
        
        all_funcs = call_chain_data.get_all_functions()
        edges = call_chain_data.get_all_edges()
        modules = call_chain_data.get_modules()
        
        roots = GraphAnalyzer.find_root_functions(call_chain_data)
        for func_name in roots:
            if func_name in all_funcs:
                all_funcs[func_name].function_type = FunctionType.ROOT
        
        circular_pairs = GraphAnalyzer.detect_circular_dependencies(call_chain_data)
        circular_set = set(tuple(sorted(p)) for p in circular_pairs)
        
        call_counts = GraphAnalyzer.calculate_call_counts(call_chain_data)
        in_out_degrees = GraphAnalyzer.calculate_in_out_degrees(call_chain_data)
        
        nodes = []
        for func_name, func_info in all_funcs.items():
            node = self._create_node(func_info, in_out_degrees, call_counts)
            nodes.append(node)
            self.node_ids[func_name] = node["id"]
        
        graph_edges = []
        for i, edge in enumerate(edges):
            edge_obj = self._create_edge(edge, i, call_counts, circular_set)
            if edge_obj:
                graph_edges.append(edge_obj)
        
        module_nodes = defaultdict(list)
        for func_name, func_info in all_funcs.items():
            module = func_info.module or "default"
            if func_name in self.node_ids:
                module_nodes[module].append(self.node_ids[func_name])
        
        module_list = []
        for i, (module_name, node_ids) in enumerate(module_nodes.items()):
            module_list.append({
                "id": f"module_{i}",
                "name": module_name,
                "nodes": node_ids,
                "color": StyleManager.get_module_color(i)
            })
        
        statistics = GraphAnalyzer.generate_statistics(call_chain_data)
        
        graph = {
            "metadata": {
                "project_name": project_name or call_chain_data.project_name or "unknown",
                "language": language or call_chain_data.language or "unknown",
                "display_mode": self.display_mode.value,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            },
            "nodes": nodes,
            "edges": graph_edges,
            "modules": module_list
        }
        
        return {
            "graph": graph,
            "statistics": statistics
        }

    def _create_node(self, func_info: FunctionInfo, 
                     in_out_degrees: Dict[str, Tuple[int, int]],
                     call_counts: Dict[Tuple[str, str], int]) -> Dict[str, Any]:
        node_id = NameManager.generate_node_id(func_info.name, self.node_ids)
        
        func_type = func_info.function_type.value
        style = StyleManager.get_style_for_function_type(func_type)
        
        in_degree, out_degree = in_out_degrees.get(func_info.name, (0, 0))
        
        total_calls = sum(
            count for (caller, callee), count in call_counts.items()
            if caller == func_info.name or callee == func_info.name
        )
        
        return {
            "id": node_id,
            "label": func_info.get_display_name(self.display_mode),
            "label_en": func_info.name,
            "label_cn": func_info.name_cn or func_info.name,
            "type": "function",
            "subtype": func_type,
            "module": func_info.module or "default",
            "file_path": func_info.file_path,
            "line_number": func_info.line_number,
            "metadata": {
                "return_type": func_info.return_type,
                "visibility": func_info.visibility,
                "in_degree": in_degree,
                "out_degree": out_degree,
                "call_count": total_calls,
                "description": func_info.description,
                "parameters": func_info.parameters,
                "docstring": func_info.docstring
            },
            "style": {
                "color": style["fill"],
                "border_color": style["stroke"],
                "border_width": int(style["stroke_width"].replace("px", "")),
                "text_color": style["color"],
                "shape": "rounded"
            }
        }

    def _create_edge(self, edge: CallEdge, index: int,
                     call_counts: Dict[Tuple[str, str], int],
                     circular_set: Set[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
        if edge.caller.name not in self.node_ids or edge.callee.name not in self.node_ids:
            return None
        
        source_id = self.node_ids[edge.caller.name]
        target_id = self.node_ids[edge.callee.name]
        
        edge_key = (edge.caller.name, edge.callee.name)
        edge_id = NameManager.generate_edge_id(source_id, target_id, index)
        
        call_type = edge.call_type.value
        edge_style = StyleManager.get_edge_style(call_type)
        
        call_count = call_counts.get(edge_key, 1)
        
        is_circular = tuple(sorted(edge_key)) in circular_set
        
        label = self._get_edge_label(edge, call_count, is_circular)
        
        return {
            "id": edge_id,
            "source": source_id,
            "target": target_id,
            "type": "calls",
            "subtype": call_type,
            "label": label,
            "metadata": {
                "call_site": edge.call_site.to_dict() if edge.call_site else None,
                "arguments": edge.arguments,
                "call_count": call_count,
                "is_conditional": edge.is_conditional,
                "is_loop": edge.is_loop,
                "is_async": edge.is_async,
                "is_circular": is_circular,
                "condition": edge.condition
            },
            "style": {
                "color": edge_style["color"],
                "width": edge_style["width"],
                "dash_style": edge_style["dash_style"],
                "arrow": "triangle"
            }
        }

    def _get_edge_label(self, edge: CallEdge, call_count: int, is_circular: bool) -> str:
        labels = []
        
        if call_count > 1:
            labels.append(f"×{call_count}")
        
        if is_circular:
            labels.append("循环依赖")
        
        if edge.call_type == CallType.ASYNC:
            labels.append("异步")
        elif edge.call_type == CallType.CONDITIONAL:
            if edge.condition:
                labels.append(f"条件: {edge.condition}")
            else:
                labels.append("条件调用")
        elif edge.call_type == CallType.LOOP:
            labels.append("循环调用")
        
        if labels:
            return " | ".join(labels)
        
        return "调用"


class EnhancedKnowledgeGraphGenerator(KnowledgeGraphGenerator):
    
    def generate_with_hierarchy(self, call_chain_data: CallChainData,
                                 project_name: Optional[str] = None,
                                 language: Optional[str] = None) -> Dict[str, Any]:
        base_graph = self.generate(call_chain_data, project_name, language)
        
        hierarchy = self._build_hierarchy(call_chain_data)
        base_graph["hierarchy"] = hierarchy
        
        layers = self._detect_layers(call_chain_data)
        base_graph["layers"] = layers
        
        return base_graph

    def _build_hierarchy(self, call_chain_data: CallChainData) -> Dict[str, Any]:
        all_funcs = call_chain_data.get_all_functions()
        edges = call_chain_data.get_all_edges()
        
        adjacency = defaultdict(list)
        reverse_adjacency = defaultdict(list)
        
        for edge in edges:
            adjacency[edge.caller.name].append(edge.callee.name)
            reverse_adjacency[edge.callee.name].append(edge.caller.name)
        
        roots = GraphAnalyzer.find_root_functions(call_chain_data)
        
        hierarchy = {
            "roots": list(roots),
            "children": {},
            "parents": {},
            "levels": {}
        }
        
        for func_name in all_funcs:
            hierarchy["children"][func_name] = adjacency.get(func_name, [])
            hierarchy["parents"][func_name] = reverse_adjacency.get(func_name, [])
        
        visited = set()
        level_map = {}
        
        def dfs_level(node: str, level: int):
            if node in visited:
                return
            visited.add(node)
            level_map[node] = level
            
            for child in adjacency[node]:
                dfs_level(child, level + 1)
        
        for root in roots:
            dfs_level(root, 0)
        
        for func_name in all_funcs:
            if func_name not in level_map:
                level_map[func_name] = 0
        
        hierarchy["levels"] = level_map
        
        return hierarchy

    def _detect_layers(self, call_chain_data: CallChainData) -> List[Dict[str, Any]]:
        all_funcs = call_chain_data.get_all_functions()
        edges = call_chain_data.get_all_edges()
        
        in_degree = defaultdict(int)
        adjacency = defaultdict(list)
        
        for edge in edges:
            adjacency[edge.caller.name].append(edge.callee.name)
            in_degree[edge.callee.name] += 1
        
        for func_name in all_funcs:
            if func_name not in in_degree:
                in_degree[func_name] = 0
        
        queue = [name for name, deg in in_degree.items() if deg == 0]
        layers = []
        processed = set()
        
        while queue:
            layer_nodes = []
            next_queue = []
            
            for node in queue:
                if node not in processed:
                    layer_nodes.append(node)
                    processed.add(node)
                    
                    for neighbor in adjacency[node]:
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0 and neighbor not in processed:
                            next_queue.append(neighbor)
            
            if layer_nodes:
                layers.append({
                    "layer_index": len(layers),
                    "nodes": layer_nodes,
                    "node_count": len(layer_nodes)
                })
            
            queue = next_queue
        
        unprocessed = set(all_funcs.keys()) - processed
        if unprocessed:
            layers.append({
                "layer_index": len(layers),
                "nodes": list(unprocessed),
                "node_count": len(unprocessed),
                "note": "包含循环依赖的节点"
            })
        
        return layers
