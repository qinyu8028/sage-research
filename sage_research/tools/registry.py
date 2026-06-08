from .base_tool import Tool


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools = {}

    def register_tool(self, tool: Tool):
        if tool.name in self.tools:
            print(f"⚠️ 警告:工具 '{tool.name}' 已存在，将被覆盖。")
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        if name in self.tools:
            tool = self.tools[name]
            return tool
        else:
            return f"⚠️ 调用工具时发生错误: 不存在名称为{name}的工具，请检查输入"

    def get_all_schemas(self) -> list:
        schemas = []
        for name, tool in self.tools.items():
            schema = tool.to_schema()
            schemas.append(schema)
        return schemas
