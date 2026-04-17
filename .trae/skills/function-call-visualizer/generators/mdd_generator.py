from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from models.data_models import (
    CallChainData, CallEdge, FunctionInfo, DisplayMode, CallType, FunctionType
)
from utils.helpers import GraphAnalyzer, NameManager, StyleManager


class MDDGenerator:
    
    def __init__(self, display_mode: DisplayMode = DisplayMode.ENGLISH):
        self.display_mode = display_mode
        self.node_ids: Dict[str, str] = {}
        self.generated_nodes: Set[str] = set()
        self.generated_edges: Set[Tuple[str, str]] = set()
        self.call_counts: Dict[Tuple[str, str], int] = {}
        self.circular_pairs: Set[Tuple[str, str]] = set()

    def generate(self, call_chain_data: CallChainData) -> str:
        self.node_ids.clear()
        self.generated_nodes.clear()
        self.generated_edges.clear()
        self.call_counts = GraphAnalyzer.calculate_call_counts(call_chain_data)
        circular = GraphAnalyzer.detect_circular_dependencies(call_chain_data)
        self.circular_pairs = set(tuple(sorted(p)) for p in circular)
        
        roots = GraphAnalyzer.find_root_functions(call_chain_data)
        all_funcs = call_chain_data.get_all_functions()
        
        for func_name, func_info in all_funcs.items():
            if func_name in roots:
                func_info.function_type = FunctionType.ROOT
        
        modules = call_chain_data.get_modules()
        
        lines = []
        lines.append("flowchart TD")
        lines.append("")
        
        lines.append("    %% 样式定义")
        for style_def in StyleManager.get_all_mermaid_class_defs():
            lines.append(f"    {style_def}")
        lines.append("")
        
        lines.append("    %% 按模块分组的函数节点")
        module_funcs = self._group_functions_by_module(call_chain_data, modules)
        
        for module_name, func_names in module_funcs.items():
            if not func_names:
                continue
            
            module_label = NameManager.sanitize_for_mermaid(module_name)
            lines.append(f"    subgraph {self._sanitize_module_name(module_name)} [{module_label}]")
            
            for func_name in func_names:
                if func_name in all_funcs:
                    func_info = all_funcs[func_name]
                    node_def = self._generate_node_definition(func_info)
                    lines.append(f"        {node_def}")
                    self.generated_nodes.add(func_name)
            
            lines.append(f"    end")
            lines.append("")
        
        lines.append("    %% 调用关系")
        edges = call_chain_data.get_all_edges()
        generated_edge_keys = set()
        
        for edge in edges:
            edge_key = (edge.caller.name, edge.callee.name)
            
            if edge_key not in generated_edge_keys:
                edge_def = self._generate_edge_definition(edge)
                if edge_def:
                    lines.append(f"    {edge_def}")
                generated_edge_keys.add(edge_key)
        
        lines.append("")
        lines.append("    %% 图例说明")
        lines.append("    subgraph 图例 [图例]")
        lines.append("        direction LR")
        lines.append("        legend_root[入口函数]:::root")
        lines.append("        legend_func[普通函数]:::func")
        lines.append("        legend_lib[库函数]:::lib")
        lines.append("        legend_class[类定义]:::class")
        lines.append("    end")
        
        return "\n".join(lines)

    def _sanitize_module_name(self, module_name: str) -> str:
        clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in module_name)
        if not clean or not clean[0].isalpha():
            clean = 'module_' + clean
        return clean

    def _group_functions_by_module(self, call_chain_data: CallChainData, 
                                     modules: Dict[str, List[str]]) -> Dict[str, List[str]]:
        all_funcs = call_chain_data.get_all_functions()
        result = defaultdict(list)
        
        for module_name, func_names in modules.items():
            for func_name in func_names:
                if func_name in all_funcs:
                    result[module_name].append(func_name)
        
        unassigned = set(all_funcs.keys()) - set().union(*result.values())
        if unassigned:
            result["未分配模块"] = list(unassigned)
        
        return dict(result)

    def _generate_node_definition(self, func_info: FunctionInfo) -> str:
        node_id = NameManager.generate_node_id(func_info.name, self.node_ids)
        label = func_info.get_mdd_label(self.display_mode)
        label = NameManager.sanitize_for_mermaid(label)
        label = NameManager.truncate_label(label)
        
        func_type = func_info.function_type.value
        
        if func_type == 'root':
            class_name = 'root'
        elif func_type == 'library':
            class_name = 'lib'
        elif func_type == 'class':
            class_name = 'class'
        else:
            class_name = 'func'
        
        return f"{node_id}[{label}]:::{class_name}"

    def _generate_edge_definition(self, edge: CallEdge) -> Optional[str]:
        if edge.caller.name not in self.node_ids or edge.callee.name not in self.node_ids:
            return None
        
        source_id = self.node_ids[edge.caller.name]
        target_id = self.node_ids[edge.callee.name]
        
        edge_style = StyleManager.get_edge_style(edge.call_type.value)
        arrow = edge_style['arrow']
        
        labels = []
        
        edge_key = (edge.caller.name, edge.callee.name)
        if edge_key in self.call_counts and self.call_counts[edge_key] > 1:
            labels.append(f"x{self.call_counts[edge_key]}")
        
        sorted_key = tuple(sorted(edge_key))
        if sorted_key in self.circular_pairs:
            labels.append("循环")
        
        if edge.call_type == CallType.ASYNC:
            labels.append("异步")
        elif edge.call_type == CallType.CONDITIONAL and edge.condition:
            labels.append(f"条件: {edge.condition}")
        elif edge.call_type == CallType.LOOP:
            labels.append("循环")
        
        label_str = "|".join(labels)
        
        if label_str:
            return f"{source_id} {arrow}|{label_str}| {target_id}"
        else:
            return f"{source_id} {arrow} {target_id}"

    def generate_with_stats(self, call_chain_data: CallChainData) -> Tuple[str, Dict]:
        mdd = self.generate(call_chain_data)
        stats = GraphAnalyzer.generate_statistics(call_chain_data)
        
        return mdd, stats


class CompactMDDGenerator(MDDGenerator):
    
    def __init__(self, display_mode: DisplayMode = DisplayMode.ENGLISH, 
                 max_nodes_per_diagram: int = 30):
        super().__init__(display_mode)
        self.max_nodes_per_diagram = max_nodes_per_diagram

    def generate_compact(self, call_chain_data: CallChainData) -> List[str]:
        all_funcs = call_chain_data.get_all_functions()
        
        if len(all_funcs) <= self.max_nodes_per_diagram:
            return [self.generate(call_chain_data)]
        
        return self._split_into_subgraphs(call_chain_data)

    def _split_into_subgraphs(self, call_chain_data: CallChainData) -> List[str]:
        diagrams = []
        modules = call_chain_data.get_modules()
        all_funcs = call_chain_data.get_all_functions()
        edges = call_chain_data.get_all_edges()
        
        modules_list = list(modules.items())
        current_funcs = {}
        current_edges = []
        
        for module_name, func_names in modules_list:
            module_funcs = {name: all_funcs[name] for name in func_names if name in all_funcs}
            
            if len(current_funcs) + len(module_funcs) > self.max_nodes_per_diagram and current_funcs:
                sub_chain_data = self._create_sub_chain_data(current_funcs, current_edges)
                diagrams.append(self.generate(sub_chain_data))
                current_funcs = {}
                current_edges = []
            
            current_funcs.update(module_funcs)
            
            for edge in edges:
                if edge.caller.name in current_funcs and edge.callee.name in current_funcs:
                    current_edges.append(edge)
        
        if current_funcs:
            sub_chain_data = self._create_sub_chain_data(current_funcs, current_edges)
            diagrams.append(self.generate(sub_chain_data))
        
        return diagrams

    def _create_sub_chain_data(self, funcs: Dict[str, FunctionInfo], 
                                 edges: List[CallEdge]) -> CallChainData:
        from models.data_models import CallChain
        
        chain = CallChain(
            chain_id="subgraph_chain",
            root_function=list(funcs.values())[0] if funcs else FunctionInfo(name="dummy"),
            calls=edges
        )
        
        return CallChainData(
            call_chains=[chain],
            function_metadata=funcs
        )
