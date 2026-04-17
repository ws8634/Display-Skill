import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from ..models.data_models import (
    Node, Edge, CallChain, GraphData, Location, Signature,
    NodeType, EdgeType, CallType
)


class FormatDetector:
    
    @staticmethod
    def detect(data: Any) -> str:
        if not isinstance(data, dict):
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    item = data[0]
                    if "source_component" in item or "target_api" in item:
                        return "call_chains"
            return "unknown"
        
        if "nodes" in data and isinstance(data["nodes"], list):
            if "edges" in data and isinstance(data["edges"], list):
                return "nodes_edges"
        
        if "call_chains" in data and isinstance(data["call_chains"], list):
            return "call_chains_dict"
        
        if "skill_version" in data or "analysis_type" in data:
            if "nodes" in data:
                return "nodes_edges"
        
        return "unknown"


class DataParser:
    
    @staticmethod
    def parse_node(node_data: Dict[str, Any]) -> Node:
        type_str = node_data.get("type", "Unknown")
        try:
            node_type = NodeType(type_str)
        except ValueError:
            node_type = NodeType.UNKNOWN
        
        location_data = node_data.get("location")
        location = None
        if location_data:
            location = Location(
                start_line=location_data.get("start_line"),
                end_line=location_data.get("end_line"),
                start_column=location_data.get("start_column"),
                end_column=location_data.get("end_column")
            )
        
        signature_data = node_data.get("signature")
        signature = None
        if signature_data:
            signature = Signature(
                parameters=signature_data.get("parameters", []),
                return_type=signature_data.get("return_type"),
                is_async=signature_data.get("is_async", False),
                is_exported=signature_data.get("is_exported", False)
            )
        
        return Node(
            id=node_data.get("id", ""),
            type=node_type,
            name=node_data.get("name", ""),
            qualified_name=node_data.get("qualified_name"),
            file_path=node_data.get("file_path"),
            location=location,
            signature=signature,
            tags=node_data.get("tags", []),
            props=node_data.get("props", []),
            state_hooks=node_data.get("state_hooks", []),
            children=node_data.get("children", []),
            method=node_data.get("method"),
            path=node_data.get("path"),
            name_cn=node_data.get("name_cn"),
            module_name=node_data.get("module_name")
        )

    @staticmethod
    def parse_edge(edge_data: Dict[str, Any], nodes_map: Dict[str, Node] = None) -> Edge:
        type_str = edge_data.get("type", "CALLS")
        try:
            edge_type = EdgeType(type_str)
        except ValueError:
            edge_type = EdgeType.CALLS
        
        call_type_str = edge_data.get("call_type")
        call_type = None
        if call_type_str:
            try:
                call_type = CallType(call_type_str)
            except ValueError:
                pass
        
        location_data = edge_data.get("location")
        location = None
        if location_data:
            location = Location(
                start_line=location_data.get("start_line"),
                end_line=location_data.get("end_line")
            )
        
        source_id = edge_data.get("source", "")
        target_id = edge_data.get("target", "")
        
        source_name = edge_data.get("source_name")
        target_name = edge_data.get("target_name")
        source_type = edge_data.get("source_type")
        target_type = edge_data.get("target_type")
        
        if nodes_map:
            if source_id in nodes_map and not source_name:
                source_name = nodes_map[source_id].name
                source_type = nodes_map[source_id].type
            if target_id in nodes_map and not target_name:
                target_name = nodes_map[target_id].name
                target_type = nodes_map[target_id].type
        
        if source_type and isinstance(source_type, str):
            try:
                source_type = NodeType(source_type)
            except ValueError:
                source_type = None
        
        if target_type and isinstance(target_type, str):
            try:
                target_type = NodeType(target_type)
            except ValueError:
                target_type = None
        
        return Edge(
            id=edge_data.get("id", f"{source_id}_to_{target_id}"),
            type=edge_type,
            call_type=call_type,
            source=source_id,
            target=target_id,
            source_name=source_name,
            target_name=target_name,
            source_type=source_type,
            target_type=target_type,
            location=location,
            arguments=edge_data.get("arguments", []),
            is_async=edge_data.get("is_async", False),
            metadata=edge_data.get("metadata", {})
        )

    @staticmethod
    def parse_call_chain(chain_data: Dict[str, Any]) -> CallChain:
        return CallChain(
            source_component=chain_data.get("source_component", ""),
            target_api=chain_data.get("target_api", ""),
            source_chinese=chain_data.get("source_chinese"),
            target_chinese=chain_data.get("target_chinese"),
            source_type=chain_data.get("source_type", "Component"),
            method=chain_data.get("method", "GET"),
            path=chain_data.get("path", ""),
            file_path=chain_data.get("file_path"),
            source_file=chain_data.get("source_file"),
            source_qualified_name=chain_data.get("source_qualified_name"),
            target_qualified_name=chain_data.get("target_qualified_name"),
            source_parameters=chain_data.get("source_parameters", []),
            metadata=chain_data.get("metadata", {})
        )


class NodesEdgesParser:
    
    @staticmethod
    def parse(data: Dict[str, Any]) -> GraphData:
        graph_data = GraphData(
            skill_version=data.get("skill_version"),
            analysis_type=data.get("analysis_type"),
            summary=data.get("summary", {}),
            source_format="nodes_edges"
        )
        
        nodes_map = {}
        for node_data in data.get("nodes", []):
            node = DataParser.parse_node(node_data)
            graph_data.nodes.append(node)
            nodes_map[node.id] = node
        
        for edge_data in data.get("edges", []):
            edge = DataParser.parse_edge(edge_data, nodes_map)
            graph_data.edges.append(edge)
        
        return graph_data


class CallChainsParser:
    
    @staticmethod
    def parse(data: Any) -> GraphData:
        graph_data = GraphData(
            source_format="call_chains"
        )
        
        if isinstance(data, list):
            chains = data
        elif isinstance(data, dict) and "call_chains" in data:
            chains = data.get("call_chains", [])
        else:
            chains = []
        
        nodes_map = {}
        
        for chain_data in chains:
            chain = DataParser.parse_call_chain(chain_data)
            graph_data.call_chains.append(chain)
            
            source_id = f"src_{chain.source_component}"
            if source_id not in nodes_map:
                source_type_str = chain.source_type or "Component"
                try:
                    source_type = NodeType(source_type_str)
                except ValueError:
                    source_type = NodeType.COMPONENT
                
                source_node = Node(
                    id=source_id,
                    type=source_type,
                    name=chain.source_component,
                    file_path=chain.source_file,
                    qualified_name=chain.source_qualified_name,
                    name_cn=chain.source_chinese
                )
                graph_data.nodes.append(source_node)
                nodes_map[source_id] = source_node
            
            target_id = f"tgt_{chain.target_api}"
            if target_id not in nodes_map:
                target_node = Node(
                    id=target_id,
                    type=NodeType.API,
                    name=chain.target_api,
                    file_path=chain.file_path,
                    qualified_name=chain.target_qualified_name,
                    name_cn=chain.target_chinese,
                    method=chain.method,
                    path=chain.path
                )
                graph_data.nodes.append(target_node)
                nodes_map[target_id] = target_node
            
            edge = Edge(
                id=f"edge_{source_id}_to_{target_id}",
                type=EdgeType.CALLS,
                call_type=CallType.API_CALL,
                source=source_id,
                target=target_id,
                source_name=chain.source_component,
                target_name=chain.target_api,
                source_type=NodeType(chain.source_type) if chain.source_type else NodeType.COMPONENT,
                target_type=NodeType.API,
                arguments=chain.source_parameters
            )
            graph_data.edges.append(edge)
        
        total_components = len([n for n in graph_data.nodes if n.type in (NodeType.COMPONENT, NodeType.FUNCTION)])
        total_apis = len([n for n in graph_data.nodes if n.type == NodeType.API])
        
        graph_data.summary = {
            "total_nodes": len(graph_data.nodes),
            "total_edges": len(graph_data.edges),
            "total_components": total_components,
            "total_apis": total_apis,
            "total_call_chains": len(graph_data.call_chains)
        }
        
        return graph_data


class UnifiedParser:
    
    @staticmethod
    def parse(data: Any) -> GraphData:
        format_type = FormatDetector.detect(data)
        
        if format_type == "nodes_edges":
            return NodesEdgesParser.parse(data)
        elif format_type in ("call_chains", "call_chains_dict"):
            return CallChainsParser.parse(data)
        else:
            if isinstance(data, dict) and "nodes" in data:
                return NodesEdgesParser.parse(data)
            elif isinstance(data, list):
                return CallChainsParser.parse(data)
            
            raise ValueError(f"无法识别的数据格式: {format_type}")

    @staticmethod
    def parse_file(file_path: str) -> GraphData:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return UnifiedParser.parse(data)


class DataValidator:
    
    @staticmethod
    def validate_nodes_edges(data: Dict[str, Any]) -> List[str]:
        errors = []
        
        if "nodes" not in data:
            errors.append("缺少 'nodes' 字段")
        elif not isinstance(data["nodes"], list):
            errors.append("'nodes' 必须是数组类型")
        
        if "edges" not in data:
            errors.append("缺少 'edges' 字段")
        elif not isinstance(data["edges"], list):
            errors.append("'edges' 必须是数组类型")
        
        if "nodes" in data and isinstance(data["nodes"], list):
            node_ids = set()
            for i, node in enumerate(data["nodes"]):
                if "id" not in node:
                    errors.append(f"nodes[{i}] 缺少 'id' 字段")
                elif node["id"] in node_ids:
                    errors.append(f"nodes[{i}] 存在重复的 id: {node['id']}")
                else:
                    node_ids.add(node["id"])
                
                if "type" not in node:
                    errors.append(f"nodes[{i}] 缺少 'type' 字段")
                if "name" not in node:
                    errors.append(f"nodes[{i}] 缺少 'name' 字段")
        
        if "edges" in data and isinstance(data["edges"], list):
            node_ids = set(n.get("id") for n in data.get("nodes", []) if n.get("id"))
            for i, edge in enumerate(data["edges"]):
                if "source" not in edge:
                    errors.append(f"edges[{i}] 缺少 'source' 字段")
                elif edge["source"] not in node_ids:
                    errors.append(f"edges[{i}] source '{edge['source']}' 不存在于 nodes 中")
                
                if "target" not in edge:
                    errors.append(f"edges[{i}] 缺少 'target' 字段")
                elif edge["target"] not in node_ids:
                    errors.append(f"edges[{i}] target '{edge['target']}' 不存在于 nodes 中")
        
        return errors

    @staticmethod
    def validate_call_chains(data: Any) -> List[str]:
        errors = []
        
        chains = []
        if isinstance(data, list):
            chains = data
        elif isinstance(data, dict) and "call_chains" in data:
            chains = data.get("call_chains", [])
        else:
            errors.append("无法识别的调用链数据格式")
            return errors
        
        for i, chain in enumerate(chains):
            if not isinstance(chain, dict):
                errors.append(f"call_chains[{i}] 必须是对象类型")
                continue
            
            if "source_component" not in chain:
                errors.append(f"call_chains[{i}] 缺少 'source_component' 字段")
            if "target_api" not in chain:
                errors.append(f"call_chains[{i}] 缺少 'target_api' 字段")
        
        return errors

    @staticmethod
    def validate(data: Any) -> Tuple[bool, List[str]]:
        format_type = FormatDetector.detect(data)
        
        if format_type == "nodes_edges":
            errors = DataValidator.validate_nodes_edges(data)
        elif format_type in ("call_chains", "call_chains_dict"):
            errors = DataValidator.validate_call_chains(data)
        else:
            errors = [f"无法识别的数据格式: {format_type}"]
        
        return len(errors) == 0, errors
