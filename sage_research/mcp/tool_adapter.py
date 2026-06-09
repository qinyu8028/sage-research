from typing import Any

from ..tools import BaseTool
from .client import MCPClient
from ..tools import ToolRegistry


class MCPTool(BaseTool):
    """
    Adapt mcp tools into our own tool base class.
    """
    def __init__(
        self, 
        original_name: str, 
        description: str, 
        input_schema: dict[str, Any],
        mcp_client: MCPClient
    ):
        self.original_name = original_name
        self.input_schema = input_schema
        self.mcp_client = mcp_client

        prefixed_name = f"mcp__{mcp_client.name}__{original_name}"
        super().__init__(name=prefixed_name, description=description, parameters=[])
        
    def run_tool(self, parameters: dict[str, Any]) -> str:
        return self.mcp_client.call_tool(self.original_name, parameters)

    def to_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }


def register_mcp_tools(registry: ToolRegistry, clients: list[MCPClient]):
    for mcp_client in clients:
        tool_list = mcp_client.tools

        for tool in tool_list:
            mcp_tool = MCPTool(
                original_name=tool.name, 
                description=tool.description, 
                input_schema=tool.inputSchema, 
                mcp_client=mcp_client
            )
            registry.register_tool(mcp_tool)
    