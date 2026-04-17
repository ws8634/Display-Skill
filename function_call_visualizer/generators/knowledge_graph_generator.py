from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
from datetime import datetime

from ..models.data_models import (
    GraphData, Node, Edge, CallChain,
    NodeType, EdgeType, CallType, DisplayMode
)
from ..utils.helpers import GraphAnalyzer, NameManager, StyleManager


class KnowledgeGraphGenerator:
    
    def __init__(self, display_mode: DisplayMode = DisplayMode.ENGLISH):
        self.display_mode = display_mode
        self.node_id_map: Dict[str, str] = {}

    def generate(self, graph_data: GraphData,
                 project_name: Optional[str] = None,
                 language: Optional[str] = None) -> Dict[str, Any]:
        self.node_id_map.clear()
        
        roots = GraphAnalyzer.find_root_nodes(graph_data)
        for node_id in roots:
            node = graph_data.get_node_by_id(node_id)
            if node:
                pass
        
        call_counts = GraphAnalyzer.calculate_call_counts(graph_data)
        in_out_degrees = GraphAnalyzer.calculate_in_out_degrees(graph_data)
        circular = GraphAnalyzer.detect_circular_dependencies(graph_data)
        circular_set = set(tuple(sorted(p)) for p in circular)
        modules = GraphAnalyzer.group_nodes_by_module(graph_data)
        
        nodes = []
        for node in graph_data.nodes:
            node_obj = self._create_node(node, in_out_degrees, call_counts, roots)
            nodes.append(node_obj)
            self.node_id_map[node.id] = node_obj["id"]
        
        edges = []
        for i, edge in enumerate(graph_data.edges):
            edge_obj = self._create_edge(edge, i, call_counts, circular_set, graph_data)
            if edge_obj:
                edges.append(edge_obj)
        
        module_list = []
        for i, (module_name, node_ids) in enumerate(modules.items()):
            module_node_ids = [self.node_id_map[nid] for nid in node_ids if nid in self.node_id_map]
            if module_node_ids:
                module_list.append({
                    "id": f"module_{i}",
                    "name": module_name,
                    "nodes": module_node_ids,
                    "color": StyleManager.get_module_color(i)
                })
        
        statistics = GraphAnalyzer.generate_statistics(graph_data)
        
        graph = {
            "metadata": {
                "project_name": project_name or graph_data.summary.get("project_name", "unknown"),
                "language": language or "typescript",
                "display_mode": self.display_mode.value,
                "source_format": graph_data.source_format,
                "skill_version": graph_data.skill_version,
                "analysis_type": graph_data.analysis_type,
                "generated_at": datetime.utcnow().isoformat() + "Z"
            },
            "nodes": nodes,
            "edges": edges,
            "modules": module_list
        }
        
        return {
            "graph": graph,
            "statistics": statistics
        }

    def _create_node(self, node: Node,
                     in_out_degrees: Dict[str, Tuple[int, int]],
                     call_counts: Dict[Tuple[str, str], int],
                     roots: Set[str]) -> Dict[str, Any]:
        is_root = node.id in roots
        style = StyleManager.get_style_for_node(node, is_root)
        
        in_degree, out_degree = in_out_degrees.get(node.id, (0, 0))
        
        total_calls = 0
        for (src, tgt), count in call_counts.items():
            if src == node.id or tgt == node.id:
                total_calls += count
        
        node_id = NameManager.generate_node_id(node.name or node.id, {})
        if node.id not in self.node_id_map:
            self.node_id_map[node.id] = node_id
        
        result = {
            "id": node_id,
            "original_id": node.id,
            "label": node.get_display_name(self.display_mode),
            "label_en": node.name,
            "label_cn": node.name_cn or node.name,
            "type": "function",
            "subtype": node.type.value.lower(),
            "module": node.module_name,
            "file_path": node.file_path,
            "is_root": is_root,
        }
        
        if node.location:
            result["location"] = {
                "start_line": node.location.start_line,
                "end_line": node.location.end_line
            }
        
        if node.signature:
            result["signature"] = {
                "parameters": node.signature.parameters,
                "return_type": node.signature.return_type,
                "is_async": node.signature.is_async,
                "is_exported": node.signature.is_exported
            }
        
        if node.type == NodeType.API:
            result["method"] = node.method
            result["path"] = node.path
        
        if node.tags:
            result["tags"] = node.tags
        
        result["metadata"] = {
            "in_degree": in_degree,
            "out_degree": out_degree,
            "total_calls": total_calls,
            "qualified_name": node.qualified_name
        }
        
        result["style"] = {
            "color": style["fill"],
            "border_color": style["stroke"],
            "border_width": int(style["stroke_width"].replace("px", "")),
            "text_color": style["color"],
            "shape": "rounded"
        }
        
        return result

    def _create_edge(self, edge: Edge, index: int,
                     call_counts: Dict[Tuple[str, str], int],
                     circular_set: Set[Tuple[str, str]],
                     graph_data: GraphData) -> Optional[Dict[str, Any]]:
        if edge.source not in self.node_id_map or edge.target not in self.node_id_map:
            return None
        
        source_id = self.node_id_map[edge.source]
        target_id = self.node_id_map[edge.target]
        
        edge_key = (edge.source, edge.target)
        edge_id = NameManager.generate_edge_id(source_id, target_id, index)
        
        edge_style = StyleManager.get_edge_style(edge.call_type)
        
        call_count = call_counts.get(edge_key, 1)
        is_circular = tuple(sorted(edge_key)) in circular_set
        
        label = self._get_edge_label(edge, call_count, is_circular, graph_data)
        
        source_node = graph_data.get_node_by_id(edge.source)
        target_node = graph_data.get_node_by_id(edge.target)
        
        result = {
            "id": edge_id,
            "source": source_id,
            "source_original_id": edge.source,
            "target": target_id,
            "target_original_id": edge.target,
            "type": edge.type.value.lower(),
            "subtype": edge.call_type.value.lower() if edge.call_type else "direct",
            "label": label,
        }
        
        if edge.location:
            result["call_site"] = {
                "file_path": None,
                "line_number": edge.location.start_line,
                "column_number": edge.location.start_column
            }
        
        result["metadata"] = {
            "call_count": call_count,
            "is_async": edge.is_async,
            "is_circular": is_circular,
            "is_cross_file": edge.call_type == CallType.CROSS_FILE,
            "is_api_call": edge.call_type == CallType.API_CALL,
            "arguments": edge.arguments,
            "source_name": edge.source_name or (source_node.name if source_node else None),
            "target_name": edge.target_name or (target_node.name if target_node else None),
        }
        
        if edge.metadata:
            result["metadata"].update(edge.metadata)
        
        result["style"] = {
            "color": edge_style["color"],
            "width": edge_style["width"],
            "dash_style": edge_style["dash_style"],
            "arrow": "triangle"
        }
        
        return result

    def _get_edge_label(self, edge: Edge, call_count: int,
                        is_circular: bool, graph_data: GraphData) -> str:
        labels = []
        
        if call_count > 1:
            labels.append(f"×{call_count}")
        
        if is_circular:
            labels.append("循环依赖")
        
        if edge.call_type == CallType.API_CALL:
            labels.append("API调用")
            target_node = graph_data.get_node_by_id(edge.target)
            if target_node and target_node.method:
                labels.append(target_node.method)
        elif edge.call_type == CallType.CROSS_FILE:
            labels.append("跨文件")
        elif edge.call_type == CallType.ASYNC:
            labels.append("异步")
        
        if labels:
            return " | ".join(labels)
        
        return "调用"


class EnhancedKnowledgeGraphGenerator(KnowledgeGraphGenerator):
    
    def generate_with_hierarchy(self, graph_data: GraphData,
                                 project_name: Optional[str] = None,
                                 language: Optional[str] = None) -> Dict[str, Any]:
        base_graph = self.generate(graph_data, project_name, language)
        
        hierarchy = self._build_hierarchy(graph_data)
        base_graph["hierarchy"] = hierarchy
        
        layers = self._detect_layers(graph_data)
        base_graph["layers"] = layers
        
        api_summary = self._generate_api_summary(graph_data)
        base_graph["api_summary"] = api_summary
        
        component_summary = self._generate_component_summary(graph_data)
        base_graph["component_summary"] = component_summary
        
        return base_graph

    def _build_hierarchy(self, graph_data: GraphData) -> Dict[str, Any]:
        adjacency = defaultdict(list)
        reverse_adjacency = defaultdict(list)
        
        for edge in graph_data.edges:
            if edge.source and edge.target:
                adjacency[edge.source].append(edge.target)
                reverse_adjacency[edge.target].append(edge.source)
        
        roots = GraphAnalyzer.find_root_nodes(graph_data)
        
        hierarchy = {
            "roots": list(roots),
            "children": {},
            "parents": {},
            "levels": {}
        }
        
        node_ids = set(n.id for n in graph_data.nodes)
        for node_id in node_ids:
            hierarchy["children"][node_id] = adjacency.get(node_id, [])
            hierarchy["parents"][node_id] = reverse_adjacency.get(node_id, [])
        
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
        
        for node_id in node_ids:
            if node_id not in level_map:
                level_map[node_id] = 0
        
        hierarchy["levels"] = level_map
        
        return hierarchy

    def _detect_layers(self, graph_data: GraphData) -> List[Dict[str, Any]]:
        in_degree = defaultdict(int)
        adjacency = defaultdict(list)
        
        node_ids = set(n.id for n in graph_data.nodes)
        
        for edge in graph_data.edges:
            if edge.source and edge.target:
                adjacency[edge.source].append(edge.target)
                in_degree[edge.target] += 1
        
        for node_id in node_ids:
            if node_id not in in_degree:
                in_degree[node_id] = 0
        
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
                node_details = []
                for node_id in layer_nodes:
                    node = graph_data.get_node_by_id(node_id)
                    if node:
                        node_details.append({
                            "id": node_id,
                            "name": node.name,
                            "type": node.type.value
                        })
                
                layers.append({
                    "layer_index": len(layers),
                    "nodes": layer_nodes,
                    "node_details": node_details,
                    "node_count": len(layer_nodes)
                })
            
            queue = next_queue
        
        unprocessed = node_ids - processed
        if unprocessed:
            node_details = []
            for node_id in unprocessed:
                node = graph_data.get_node_by_id(node_id)
                if node:
                    node_details.append({
                        "id": node_id,
                        "name": node.name,
                        "type": node.type.value
                    })
            
            layers.append({
                "layer_index": len(layers),
                "nodes": list(unprocessed),
                "node_details": node_details,
                "node_count": len(unprocessed),
                "note": "包含循环依赖的节点"
            })
        
        return layers

    def _generate_api_summary(self, graph_data: GraphData) -> Dict[str, Any]:
        api_nodes = graph_data.get_nodes_by_type(NodeType.API)
        
        if not api_nodes:
            return {"total_apis": 0, "methods": {}, "apis": []}
        
        method_counts = defaultdict(int)
        api_details = []
        
        for node in api_nodes:
            method = node.method or "UNKNOWN"
            method_counts[method] += 1
            
            api_details.append({
                "id": node.id,
                "name": node.name,
                "name_cn": node.name_cn,
                "method": method,
                "path": node.path,
                "file_path": node.file_path,
                "qualified_name": node.qualified_name
            })
        
        return {
            "total_apis": len(api_nodes),
            "methods": dict(method_counts),
            "apis": api_details
        }

    def _generate_component_summary(self, graph_data: GraphData) -> Dict[str, Any]:
        component_nodes = [n for n in graph_data.nodes if n.type in (NodeType.COMPONENT, NodeType.FUNCTION)]
        
        if not component_nodes:
            return {"total_components": 0, "components": []}
        
        component_details = []
        
        for node in component_nodes:
            component_details.append({
                "id": node.id,
                "name": node.name,
                "name_cn": node.name_cn,
                "type": node.type.value,
                "file_path": node.file_path,
                "qualified_name": node.qualified_name,
                "is_async": node.signature.is_async if node.signature else False,
                "is_exported": node.signature.is_exported if node.signature else False
            })
        
        return {
            "total_components": len(component_nodes),
            "components": component_details
        }
