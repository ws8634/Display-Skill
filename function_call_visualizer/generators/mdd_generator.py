from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict

from ..models.data_models import (
    GraphData, Node, Edge, CallChain,
    NodeType, EdgeType, CallType, DisplayMode
)
from ..utils.helpers import GraphAnalyzer, NameManager, StyleManager


class MDDGenerator:
    
    def __init__(self, display_mode: DisplayMode = DisplayMode.ENGLISH):
        self.display_mode = display_mode
        self.node_id_map: Dict[str, str] = {}
        self.generated_nodes: Set[str] = set()

    def generate(self, graph_data: GraphData) -> str:
        self.node_id_map.clear()
        self.generated_nodes.clear()
        
        lines = []
        lines.append("flowchart TD")
        lines.append("")
        
        lines.append("    %% 样式定义")
        for style_def in StyleManager.get_all_mermaid_class_defs():
            lines.append(f"    {style_def}")
        lines.append("")
        
        roots = GraphAnalyzer.find_root_nodes(graph_data)
        call_counts = GraphAnalyzer.calculate_call_counts(graph_data)
        circular = GraphAnalyzer.detect_circular_dependencies(graph_data)
        circular_set = set(tuple(sorted(p)) for p in circular)
        
        modules = GraphAnalyzer.group_nodes_by_module(graph_data)
        
        lines.append("    %% 按模块分组的节点")
        
        node_to_module = {}
        for module_name, node_ids in modules.items():
            for node_id in node_ids:
                node_to_module[node_id] = module_name
        
        for module_name, node_ids in modules.items():
            module_nodes = []
            for node_id in node_ids:
                node = graph_data.get_node_by_id(node_id)
                if node:
                    module_nodes.append(node)
            
            if not module_nodes:
                continue
            
            module_label = NameManager.sanitize_for_mermaid(module_name)
            lines.append(f"    subgraph {self._sanitize_module_name(module_name)} [{module_label}]")
            
            for node in module_nodes:
                is_root = node.id in roots
                node_def = self._generate_node_definition(node, is_root)
                lines.append(f"        {node_def}")
                self.generated_nodes.add(node.id)
            
            lines.append(f"    end")
            lines.append("")
        
        lines.append("    %% 调用关系")
        generated_edges = set()
        
        for edge in graph_data.edges:
            edge_key = (edge.source, edge.target)
            if edge_key in generated_edges:
                continue
            
            if edge.source not in self.generated_nodes or edge.target not in self.generated_nodes:
                continue
            
            edge_def = self._generate_edge_definition(
                edge, call_counts, circular_set, graph_data
            )
            if edge_def:
                lines.append(f"    {edge_def}")
            generated_edges.add(edge_key)
        
        lines.append("")
        lines.append("    %% 图例说明")
        lines.append("    subgraph 图例 [图例]")
        lines.append("        direction LR")
        lines.append("        legend_root[入口/组件]:::root")
        lines.append("        legend_component[React组件]:::component")
        lines.append("        legend_function[普通函数]:::function")
        lines.append("        legend_api[API端点]:::api")
        lines.append("    end")
        
        return "\n".join(lines)

    def _sanitize_module_name(self, module_name: str) -> str:
        clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in module_name)
        if not clean or not clean[0].isalpha():
            clean = 'module_' + clean
        return clean

    def _generate_node_id(self, node: Node) -> str:
        if node.id in self.node_id_map:
            return self.node_id_map[node.id]
        
        base_name = node.name
        if not base_name:
            base_name = node.id
        
        node_id = NameManager.generate_node_id(base_name, self.node_id_map)
        self.node_id_map[node.id] = node_id
        return node_id

    def _generate_node_definition(self, node: Node, is_root: bool = False) -> str:
        node_id = self._generate_node_id(node)
        
        label = node.get_mdd_label(self.display_mode)
        label = NameManager.sanitize_for_mermaid(label)
        label = NameManager.truncate_label(label)
        
        if node.type == NodeType.API:
            if node.method and node.path:
                extra_info = f"<br/>{node.method} {node.path}"
                if '<br/>' in label:
                    label = label.rsplit('<br/>', 1)[0] + extra_info + '<br/>' + label.rsplit('<br/>', 1)[1] if '<br/>' in label else label + extra_info
                else:
                    label = label + extra_info
        
        class_name = StyleManager.get_mermaid_class_name(node.type, is_root)
        
        if node.type == NodeType.API:
            shape = "([{label}])"
        elif is_root or node.type == NodeType.COMPONENT:
            shape = "[{label}]"
        else:
            shape = "[{label}]"
        
        node_shape = shape.format(label=label)
        
        return f"{node_id}{node_shape}:::{class_name}"

    def _generate_edge_definition(self, edge: Edge, 
                                   call_counts: Dict[Tuple[str, str], int],
                                   circular_set: Set[Tuple[str, str]],
                                   graph_data: GraphData) -> Optional[str]:
        if edge.source not in self.node_id_map or edge.target not in self.node_id_map:
            return None
        
        source_id = self.node_id_map[edge.source]
        target_id = self.node_id_map[edge.target]
        
        edge_style = StyleManager.get_edge_style(edge.call_type)
        arrow = edge_style['arrow']
        
        labels = []
        
        edge_key = (edge.source, edge.target)
        if edge_key in call_counts and call_counts[edge_key] > 1:
            labels.append(f"×{call_counts[edge_key]}")
        
        sorted_key = tuple(sorted(edge_key))
        if sorted_key in circular_set:
            labels.append("循环")
        
        if edge.call_type == CallType.API_CALL:
            target_node = graph_data.get_node_by_id(edge.target)
            if target_node and target_node.method:
                labels.append(target_node.method)
        
        if edge.call_type == CallType.ASYNC:
            labels.append("异步")
        elif edge.call_type == CallType.CROSS_FILE:
            labels.append("跨文件")
        
        source_node = graph_data.get_node_by_id(edge.source)
        target_node = graph_data.get_node_by_id(edge.target)
        
        if source_node and target_node:
            if source_node.type == NodeType.COMPONENT and target_node.type == NodeType.API:
                labels.insert(0, "API调用")
        
        label_str = "|".join(labels)
        
        if label_str:
            return f"{source_id} {arrow}|{label_str}| {target_id}"
        else:
            return f"{source_id} {arrow} {target_id}"

    def generate_with_stats(self, graph_data: GraphData) -> Tuple[str, Dict[str, Any]]:
        mdd = self.generate(graph_data)
        stats = GraphAnalyzer.generate_statistics(graph_data)
        return mdd, stats


class CompactMDDGenerator(MDDGenerator):
    
    def __init__(self, display_mode: DisplayMode = DisplayMode.ENGLISH,
                 max_nodes_per_diagram: int = 40):
        super().__init__(display_mode)
        self.max_nodes_per_diagram = max_nodes_per_diagram

    def generate_compact(self, graph_data: GraphData) -> List[str]:
        if len(graph_data.nodes) <= self.max_nodes_per_diagram:
            return [self.generate(graph_data)]
        
        return self._split_by_module(graph_data)

    def _split_by_module(self, graph_data: GraphData) -> List[str]:
        from ..models.data_models import GraphData as GD
        
        diagrams = []
        modules = GraphAnalyzer.group_nodes_by_module(graph_data)
        
        current_nodes = {}
        current_edges = []
        
        for module_name, node_ids in modules.items():
            module_node_map = {}
            for node_id in node_ids:
                node = graph_data.get_node_by_id(node_id)
                if node:
                    module_node_map[node_id] = node
            
            if len(current_nodes) + len(module_node_map) > self.max_nodes_per_diagram and current_nodes:
                sub_graph = self._create_sub_graph(current_nodes, current_edges, graph_data)
                diagrams.append(self.generate(sub_graph))
                current_nodes = {}
                current_edges = []
            
            current_nodes.update(module_node_map)
            
            for edge in graph_data.edges:
                if edge.source in current_nodes and edge.target in current_nodes:
                    current_edges.append(edge)
        
        if current_nodes:
            sub_graph = self._create_sub_graph(current_nodes, current_edges, graph_data)
            diagrams.append(self.generate(sub_graph))
        
        return diagrams

    def _create_sub_graph(self, nodes: Dict[str, Node], edges: List[Edge], 
                          original_graph: GraphData) -> GraphData:
        from ..models.data_models import GraphData as GD
        
        return GD(
            skill_version=original_graph.skill_version,
            analysis_type=original_graph.analysis_type,
            summary=original_graph.summary,
            nodes=list(nodes.values()),
            edges=edges,
            source_format=original_graph.source_format
        )


class APICallMDDGenerator(MDDGenerator):
    
    def __init__(self, display_mode: DisplayMode = DisplayMode.ENGLISH):
        super().__init__(display_mode)

    def generate_api_calls(self, graph_data: GraphData) -> str:
        self.node_id_map.clear()
        self.generated_nodes.clear()
        
        api_edges = [e for e in graph_data.edges if e.call_type == CallType.API_CALL]
        
        if not api_edges:
            return "%% 没有找到API调用关系"
        
        lines = []
        lines.append("flowchart LR")
        lines.append("")
        
        lines.append("    %% 样式定义")
        for style_def in StyleManager.get_all_mermaid_class_defs():
            lines.append(f"    {style_def}")
        lines.append("")
        
        component_nodes = set()
        api_nodes = set()
        
        for edge in api_edges:
            component_nodes.add(edge.source)
            api_nodes.add(edge.target)
        
        lines.append("    subgraph 前端组件 [前端组件]")
        for node_id in component_nodes:
            node = graph_data.get_node_by_id(node_id)
            if node:
                node_def = self._generate_node_definition(node, is_root=True)
                lines.append(f"        {node_def}")
                self.generated_nodes.add(node_id)
        lines.append("    end")
        lines.append("")
        
        lines.append("    subgraph 后端API [后端API端点]")
        for node_id in api_nodes:
            node = graph_data.get_node_by_id(node_id)
            if node:
                node_def = self._generate_node_definition(node, is_root=False)
                lines.append(f"        {node_def}")
                self.generated_nodes.add(node_id)
        lines.append("    end")
        lines.append("")
        
        lines.append("    %% API调用关系")
        call_counts = GraphAnalyzer.calculate_call_counts(graph_data)
        circular = GraphAnalyzer.detect_circular_dependencies(graph_data)
        circular_set = set(tuple(sorted(p)) for p in circular)
        
        for edge in api_edges:
            edge_def = self._generate_edge_definition(
                edge, call_counts, circular_set, graph_data
            )
            if edge_def:
                lines.append(f"    {edge_def}")
        
        return "\n".join(lines)
