import json
import os
import asyncio
import threading
from concurrent.futures import Future

from typing import Any
from mcp.types import CallToolResult, Tool
from pydantic import BaseModel
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession


class MCPServerConfig(BaseModel):
    name: str
    command: str
    args: list[str]
    env: dict[str, str] | None = None

    def to_stdio_params(self) -> StdioServerParameters:
        env = {**os.environ, **self.env} if self.env else os.environ
        config = StdioServerParameters(
            command=self.command, 
            args=self.args, 
            env=env,
        )
        return config


class MCPClient:
    def __init__(self, config: MCPServerConfig) -> None:
        self.name = config.name
        self.server_config: StdioServerParameters = config.to_stdio_params()
        self._thread = None
        self._queue = None
        self._ready_event = None
        self._loop = None
        self._connect_error = None
        self.tools = []

    def connect(self) -> list[Tool]:
        self._queue = asyncio.Queue()

        self._ready_event = threading.Event()
        self._thread = threading.Thread(target=self._run_background, daemon=True)
        self._thread.start()

        self._ready_event.wait()

        if self._connect_error:
            raise self._connect_error

        return self.tools

    def _run_background(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        self._loop = asyncio.get_running_loop()

        try:
            async with stdio_client(self.server_config) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.tools = (await session.list_tools()).tools
                    # (
                    #     self._session.list_tools(),
                    #     await self._session.list_resources(),
                    #     await self._session.list_prompts(),
                    # )
                    self._connect_error = None
                    self._ready_event.set()

                    while True:
                        command = await self._queue.get()
                        if command is None:
                            break

                        future: Future
                        name, args, future = command
                        try:
                            result = await session.call_tool(name=name, arguments=args)
                            future.set_result(result)
                        except Exception as e:
                            future.set_exception(e)
        except Exception as e:
            self._connect_error = e
            self._ready_event.set()

    def call_tool(self, name: str, args: dict[str, Any]):
        if self._loop is None:
            raise RuntimeError("MCPClient 未连接")
        future = Future()
        self._loop.call_soon_threadsafe(self._queue.put_nowait, (name, args, future))
        result: CallToolResult = future.result()

        if result.isError:
            return f"工具调用失败: {result.content[0].text}"
        return "\n".join(item.text for item in result.content)

    def disconnect(self):
        if self._thread is None:
            return
        self._loop.call_soon_threadsafe(self._queue.put_nowait, None)
        self._thread.join()
        self._loop = None


def create_mcp_clients(json_path: str) -> list[MCPClient]:
    with open(json_path, "r", encoding="utf-8") as f:
        configs: dict[str, dict] = json.load(f)

    server_configs: list[MCPServerConfig] = []
    for name, config in configs.items():
        env: dict[str, str] = config.get("env")
        if env:
            for key, value in env.items():
                if value.startswith("${") and value.endswith("}"):
                    env[key] = os.getenv(value[2:-1])

        server_config = MCPServerConfig(name=name, command=config["command"], args=config["args"], env=env)
        server_configs.append(server_config)

    clients = []
    for config in server_configs:
        client = MCPClient(config)
        client.connect()
        clients.append(client)

    return clients
