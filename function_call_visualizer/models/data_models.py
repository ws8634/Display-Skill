from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import json
from collections import defaultdict


class NodeType(Enum):
    FUNCTION = "Function"
    COMPONENT = "Component"
    API = "API"
    MODULE = "Module"
    CLASS = "Class"
    UNKNOWN = "Unknown"


class EdgeType(Enum):
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    REFERENCES = "REFERENCES"


class CallType(Enum):
    DIRECT = "direct"
    CROSS_FILE = "cross_file"
    API_CALL = "api_call"
    ASYNC = "async"


class DisplayMode(Enum):
    ENGLISH = "english"
    CHINESE = "chinese"
    BOTH = "both"


class OutputType(Enum):
    MDD = "mdd"
    KNOWLEDGE_GRAPH = "knowledge-graph"


@dataclass
class Location:
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    start_column: Optional[int] = None
    end_column: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.start_line is not None:
            result["start_line"] = self.start_line
        if self.end_line is not None:
            result["end_line"] = self.end_line
        if self.start_column is not None:
            result["start_column"] = self.start_column
        if self.end_column is not None:
            result["end_column"] = self.end_column
        return result


@dataclass
class Signature:
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    is_async: bool = False
    is_exported: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameters": self.parameters,
            "return_type": self.return_type,
            "is_async": self.is_async,
            "is_exported": self.is_exported
        }


@dataclass
class Node:
    id: str
    type: NodeType
    name: str
    qualified_name: Optional[str] = None
    file_path: Optional[str] = None
    location: Optional[Location] = None
    signature: Optional[Signature] = None
    tags: List[str] = field(default_factory=list)
    props: List[Any] = field(default_factory=list)
    state_hooks: List[Any] = field(default_factory=list)
    children: List[Any] = field(default_factory=list)
    
    method: Optional[str] = None
    path: Optional[str] = None
    
    name_cn: Optional[str] = None
    module_name: Optional[str] = None

    def get_display_name(self, display_mode: DisplayMode) -> str:
        if display_mode == DisplayMode.ENGLISH:
            return self.name
        elif display_mode == DisplayMode.CHINESE:
            return self.name_cn or self.name
        elif display_mode == DisplayMode.BOTH:
            if self.name_cn:
                return f"{self.name} ({self.name_cn})"
            else:
                return self.name
        return self.name

    def get_mdd_label(self, display_mode: DisplayMode) -> str:
        if display_mode == DisplayMode.BOTH and self.name_cn:
            return f"{self.name}<br/>{self.name_cn}"
        return self.get_display_name(display_mode)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file_path": self.file_path,
            "location": self.location.to_dict() if self.location else None,
            "signature": self.signature.to_dict() if self.signature else None,
            "tags": self.tags,
            "name_cn": self.name_cn,
            "module_name": self.module_name
        }
        
        if self.method:
            result["method"] = self.method
        if self.path:
            result["path"] = self.path
        
        return result


@dataclass
class Edge:
    id: str
    type: EdgeType
    call_type: Optional[CallType] = None
    source: str = ""
    target: str = ""
    source_name: Optional[str] = None
    target_name: Optional[str] = None
    source_type: Optional[NodeType] = None
    target_type: Optional[NodeType] = None
    location: Optional[Location] = None
    arguments: List[str] = field(default_factory=list)
    is_async: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "call_type": self.call_type.value if self.call_type else None,
            "source": self.source,
            "target": self.target,
            "source_name": self.source_name,
            "target_name": self.target_name,
            "source_type": self.source_type.value if self.source_type else None,
            "target_type": self.target_type.value if self.target_type else None,
            "location": self.location.to_dict() if self.location else None,
            "arguments": self.arguments,
            "is_async": self.is_async,
            "metadata": self.metadata
        }


@dataclass
class CallChain:
    source_component: str
    target_api: str
    source_chinese: Optional[str] = None
    target_chinese: Optional[str] = None
    source_type: str = "Component"
    method: str = "GET"
    path: str = ""
    file_path: Optional[str] = None
    source_file: Optional[str] = None
    source_qualified_name: Optional[str] = None
    target_qualified_name: Optional[str] = None
    source_parameters: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_component": self.source_component,
            "source_chinese": self.source_chinese,
            "source_type": self.source_type,
            "target_api": self.target_api,
            "target_chinese": self.target_chinese,
            "method": self.method,
            "path": self.path,
            "file_path": self.file_path,
            "source_file": self.source_file,
            "source_qualified_name": self.source_qualified_name,
            "target_qualified_name": self.target_qualified_name,
            "source_parameters": self.source_parameters,
            "metadata": self.metadata
        }


@dataclass
class GraphData:
    skill_version: Optional[str] = None
    analysis_type: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    call_chains: List[CallChain] = field(default_factory=list)
    source_format: str = "unknown"

    def get_node_by_id(self, node_id: str) -> Optional[Node]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        return [n for n in self.nodes if n.type == node_type]

    def get_edges_by_call_type(self, call_type: CallType) -> List[Edge]:
        return [e for e in self.edges if e.call_type == call_type]

    def get_api_call_edges(self) -> List[Edge]:
        return self.get_edges_by_call_type(CallType.API_CALL)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_version": self.skill_version,
            "analysis_type": self.analysis_type,
            "summary": self.summary,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "call_chains": [c.to_dict() for c in self.call_chains],
            "source_format": self.source_format
        }
