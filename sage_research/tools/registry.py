from typing import Any
from .base_tool import BaseTool


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools: dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        if tool.name in self.tools:
            print(f"⚠️ 警告:工具 '{tool.name}' 已存在，将被覆盖。")
        self.tools[tool.name] = tool

    def get_tools(self, whitelist: list[str]) -> list[BaseTool]:
        tool_list = []
        for name in whitelist:
            if name in self.tools:
                tool = self.tools[name]
                tool_list.append(tool)
            else:
                raise ValueError(f"⚠️ 调用工具时发生错误: 不存在名称为{name}的工具，请检查输入")

        return tool_list

    def get_schemas(self, whitelist: list[str]) -> list[dict[str, Any]]:
        schemas = []
        for name in whitelist:
            if name in self.tools:
                schema = self.tools[name].to_schema()
                schemas.append(schema)
            else:
                raise ValueError(f"⚠️ 调用工具时发生错误: 不存在名称为{name}的工具，请检查输入")

        return schemas
