from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json


class DisplayMode(Enum):
    ENGLISH = "english"
    CHINESE = "chinese"
    BOTH = "both"


class OutputType(Enum):
    MDD = "mdd"
    KNOWLEDGE_GRAPH = "knowledge-graph"


class FunctionType(Enum):
    ROOT = "root"
    REGULAR = "regular"
    LIBRARY = "library"
    CLASS = "class"


class CallType(Enum):
    SYNC = "sync"
    ASYNC = "async"
    CONDITIONAL = "conditional"
    LOOP = "loop"


@dataclass
class FunctionInfo:
    name: str
    name_cn: Optional[str] = None
    module: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    description: Optional[str] = None
    return_type: Optional[str] = None
    parameters: List[Dict[str, str]] = field(default_factory=list)
    docstring: Optional[str] = None
    visibility: str = "public"
    function_type: FunctionType = FunctionType.REGULAR

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
        return {
            "name": self.name,
            "name_cn": self.name_cn,
            "module": self.module,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "description": self.description,
            "return_type": self.return_type,
            "parameters": self.parameters,
            "docstring": self.docstring,
            "visibility": self.visibility,
            "function_type": self.function_type.value
        }


@dataclass
class CallSite:
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number
        }


@dataclass
class CallEdge:
    caller: FunctionInfo
    callee: FunctionInfo
    call_site: Optional[CallSite] = None
    arguments: List[str] = field(default_factory=list)
    is_async: bool = False
    call_type: CallType = CallType.SYNC
    call_count: int = 1
    is_conditional: bool = False
    is_loop: bool = False
    condition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "caller": self.caller.to_dict(),
            "callee": self.callee.to_dict(),
            "call_site": self.call_site.to_dict() if self.call_site else None,
            "arguments": self.arguments,
            "is_async": self.is_async,
            "call_type": self.call_type.value,
            "call_count": self.call_count,
            "is_conditional": self.is_conditional,
            "is_loop": self.is_loop,
            "condition": self.condition
        }


@dataclass
class CallChain:
    chain_id: str
    root_function: FunctionInfo
    calls: List[CallEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "root_function": self.root_function.to_dict(),
            "calls": [call.to_dict() for call in self.calls]
        }


@dataclass
class CallChainData:
    project_name: Optional[str] = None
    language: Optional[str] = None
    call_chains: List[CallChain] = field(default_factory=list)
    function_metadata: Dict[str, FunctionInfo] = field(default_factory=dict)

    def get_all_functions(self) -> Dict[str, FunctionInfo]:
        all_funcs = {}
        
        for func_name, func_info in self.function_metadata.items():
            all_funcs[func_name] = func_info
        
        for chain in self.call_chains:
            if chain.root_function.name not in all_funcs:
                all_funcs[chain.root_function.name] = chain.root_function
            
            for call in chain.calls:
                if call.caller.name not in all_funcs:
                    all_funcs[call.caller.name] = call.caller
                if call.callee.name not in all_funcs:
                    all_funcs[call.callee.name] = call.callee
        
        return all_funcs

    def get_all_edges(self) -> List[CallEdge]:
        edges = []
        for chain in self.call_chains:
            edges.extend(chain.calls)
        return edges

    def get_modules(self) -> Dict[str, List[str]]:
        modules = {}
        all_funcs = self.get_all_functions()
        
        for func_name, func_info in all_funcs.items():
            module = func_info.module or "default"
            if module not in modules:
                modules[module] = []
            if func_name not in modules[module]:
                modules[module].append(func_name)
        
        return modules

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "language": self.language,
            "call_chains": [chain.to_dict() for chain in self.call_chains],
            "function_metadata": {k: v.to_dict() for k, v in self.function_metadata.items()}
        }


class DataValidator:
    
    @staticmethod
    def validate_json(data: Dict[str, Any]) -> List[str]:
        errors = []
        
        if "call_chains" not in data:
            errors.append("缺少必填字段: call_chains")
        else:
            if not isinstance(data["call_chains"], list):
                errors.append("call_chains 必须是列表类型")
            else:
                for i, chain in enumerate(data["call_chains"]):
                    chain_errors = DataValidator._validate_call_chain(chain, i)
                    errors.extend(chain_errors)
        
        return errors

    @staticmethod
    def _validate_call_chain(chain: Dict[str, Any], index: int) -> List[str]:
        errors = []
        
        if "root_function" not in chain:
            errors.append(f"call_chains[{index}] 缺少必填字段: root_function")
        else:
            root_errors = DataValidator._validate_function_info(chain["root_function"], f"call_chains[{index}].root_function")
            errors.extend(root_errors)
        
        if "calls" not in chain:
            errors.append(f"call_chains[{index}] 缺少必填字段: calls")
        else:
            if not isinstance(chain["calls"], list):
                errors.append(f"call_chains[{index}].calls 必须是列表类型")
            else:
                for j, call in enumerate(chain["calls"]):
                    call_errors = DataValidator._validate_call_edge(call, f"call_chains[{index}].calls[{j}]")
                    errors.extend(call_errors)
        
        return errors

    @staticmethod
    def _validate_function_info(func: Dict[str, Any], path: str) -> List[str]:
        errors = []
        
        if "name" not in func:
            errors.append(f"{path} 缺少必填字段: name")
        
        return errors

    @staticmethod
    def _validate_call_edge(call: Dict[str, Any], path: str) -> List[str]:
        errors = []
        
        if "caller" not in call:
            errors.append(f"{path} 缺少必填字段: caller")
        else:
            caller_errors = DataValidator._validate_function_info(call["caller"], f"{path}.caller")
            errors.extend(caller_errors)
        
        if "callee" not in call:
            errors.append(f"{path} 缺少必填字段: callee")
        else:
            callee_errors = DataValidator._validate_function_info(call["callee"], f"{path}.callee")
            errors.extend(callee_errors)
        
        return errors


class DataParser:
    
    @staticmethod
    def parse_function_info(data: Dict[str, Any]) -> FunctionInfo:
        func_type_str = data.get("function_type", "regular")
        try:
            func_type = FunctionType(func_type_str)
        except ValueError:
            func_type = FunctionType.REGULAR
        
        return FunctionInfo(
            name=data["name"],
            name_cn=data.get("name_cn"),
            module=data.get("module"),
            file_path=data.get("file_path"),
            line_number=data.get("line_number"),
            description=data.get("description"),
            return_type=data.get("return_type"),
            parameters=data.get("parameters", []),
            docstring=data.get("docstring"),
            visibility=data.get("visibility", "public"),
            function_type=func_type
        )

    @staticmethod
    def parse_call_site(data: Optional[Dict[str, Any]]) -> Optional[CallSite]:
        if data is None:
            return None
        return CallSite(
            file_path=data.get("file_path"),
            line_number=data.get("line_number"),
            column_number=data.get("column_number")
        )

    @staticmethod
    def parse_call_edge(data: Dict[str, Any]) -> CallEdge:
        call_type_str = data.get("call_type", "sync")
        try:
            call_type = CallType(call_type_str)
        except ValueError:
            call_type = CallType.SYNC
        
        if data.get("is_async"):
            call_type = CallType.ASYNC
        
        return CallEdge(
            caller=DataParser.parse_function_info(data["caller"]),
            callee=DataParser.parse_function_info(data["callee"]),
            call_site=DataParser.parse_call_site(data.get("call_site")),
            arguments=data.get("arguments", []),
            is_async=data.get("is_async", False),
            call_type=call_type,
            call_count=data.get("call_count", 1),
            is_conditional=data.get("is_conditional", False),
            is_loop=data.get("is_loop", False),
            condition=data.get("condition")
        )

    @staticmethod
    def parse_call_chain(data: Dict[str, Any]) -> CallChain:
        return CallChain(
            chain_id=data.get("chain_id", "default_chain"),
            root_function=DataParser.parse_function_info(data["root_function"]),
            calls=[DataParser.parse_call_edge(call) for call in data.get("calls", [])]
        )

    @staticmethod
    def parse_call_chain_data(data: Dict[str, Any]) -> CallChainData:
        function_metadata = {}
        if "function_metadata" in data:
            for name, func_data in data["function_metadata"].items():
                function_metadata[name] = DataParser.parse_function_info(func_data)
        
        return CallChainData(
            project_name=data.get("project_name"),
            language=data.get("language"),
            call_chains=[DataParser.parse_call_chain(chain) for chain in data.get("call_chains", [])],
            function_metadata=function_metadata
        )

    @staticmethod
    def load_from_json_file(file_path: str) -> CallChainData:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        errors = DataValidator.validate_json(data)
        if errors:
            raise ValueError(f"JSON数据验证失败:\n" + "\n".join(errors))
        
        return DataParser.parse_call_chain_data(data)
