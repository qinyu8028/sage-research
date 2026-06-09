from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None

class BaseTool(ABC):
    """工具基类"""
    def __init__(self, name: str, description: str, parameters: list[ToolParameter]):
        self.name = name
        self.description = description
        self.parameters = parameters

    @abstractmethod
    def run_tool(self, parameters: dict[str, Any]) -> str:
        pass

    def to_schema(self):
        openai_schema = {
            "type": "function", 
            "function": {
                "name": self.name, 
                "description": self.description,
                "parameters": {
                    "type": "object", 
                    "properties": {}, 
                    "required": []
                }
            } 
        }
        properties = openai_schema["function"]["parameters"]["properties"]
        required = openai_schema["function"]["parameters"]["required"]

        for parameter in self.parameters:
            properties[parameter.name] = {
                "type": parameter.type, 
                "description": parameter.description
            }
            if parameter.required:
                required.append(parameter.name)

        return openai_schema