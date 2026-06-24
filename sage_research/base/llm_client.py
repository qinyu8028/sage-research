import json
import os, logging, time
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall, Function,
)
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

MODEL_PROFILES = {
    "deepseek": {
        "api_key": "DEEPSEEK_API_KEY",
        "base_url": "DEEPSEEK_BASE_URL",
        "extra_body": {"thinking": {"type": "disabled"}},
    },
    "glm": {
        "api_key": "GLM_API_KEY",
        "base_url": "GLM_BASE_URL",
    },
    "gemini": {
        "api_key": "GOOGLE_API_KEY",
        "base_url": "GOOGLE_BASE_URL",
    },
    "gpt": {
        "api_key": "OPENAI_API_KEY",
    },
    "qwen": {
        "api_key": "DASHSCOPE_API_KEY",
        "base_url": "DASHSCOPE_BASE_URL",
    },
}


def _resolve_model_env(model: str) -> tuple[str, str | None, dict | None]:
    for prefix, profile in MODEL_PROFILES.items():
        if model.lower().startswith(prefix):
            api_key_env = profile["api_key"]
            if not os.getenv(api_key_env):
                raise ValueError(
                    f"模型 '{model}' 匹配到 '{prefix}'，"
                    f"但环境变量 {api_key_env} 未设置"
                )

            base_url = None
            if "base_url" in profile:
                base_url_env = profile["base_url"]
                base_url = os.getenv(base_url_env)
                if not base_url:
                    raise ValueError(
                        f"模型 '{model}' 匹配到 '{prefix}'，"
                        f"但环境变量 {base_url_env} 未设置"
                    )

            return (
                os.getenv(api_key_env),
                base_url,
                profile.get("extra_body"),
            )

    all_prefixes = list(MODEL_PROFILES.keys()) + ["claude"]
    raise ValueError(
        f"未知模型 '{model}'，支持的前缀: {all_prefixes}。"
        f"请在 MODEL_PROFILES 中添加配置，或显式传入 api_key/base_url。"
    )


class LLMClient:
    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        timeout: int = None,
    ):
        self.model = model or os.getenv("LLM_MODEL_ID")
        if not self.model:
            raise ValueError("未指定模型。请使用 --model 参数或在 .env 中设置 LLM_MODEL_ID")

        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))
        self._is_claude = self.model.lower().startswith("claude")

        if self._is_claude:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "Claude 模型需要安装 anthropic SDK: pip install anthropic"
                )
            _api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not _api_key:
                raise ValueError("Claude 模型需要设置环境变量 ANTHROPIC_API_KEY")
            self._anthropic_client = anthropic.Anthropic(
                api_key=_api_key, timeout=self.timeout
            )
            self.extra_body = None
            self.client = None
        else:
            if api_key and base_url:
                self.extra_body = None
            else:
                api_key, base_url, self.extra_body = _resolve_model_env(self.model)
            self.client = OpenAI(
                api_key=api_key, base_url=base_url, timeout=self.timeout
            )

        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_calls = 0

    def invoke(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0,
        tools=None,
        tool_choice=None,
        max_tokens: int = 4096,
        tag: str = "",
    ) -> ChatCompletionMessage:
        if self._is_claude:
            return self._invoke_claude(
                messages, temperature, tools, tool_choice, max_tokens, tag
            )

        if tool_choice is None:
            tool_choice = "auto" if tools else None

        start = time.time()
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            tools=tools if tools else None,
            extra_body=self.extra_body,
        )
        elapsed = time.time() - start

        msg = response.choices[0].message
        self._track_usage(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            elapsed, tag, msg,
        )
        return msg

    # ---- Claude adapter ----

    def _invoke_claude(self, messages, temperature, tools, tool_choice, max_tokens, tag):
        system, anthropic_msgs = self._translate_messages(messages)

        anthropic_tools = None
        if tools:
            anthropic_tools = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"]["parameters"],
                }
                for t in tools
            ]

        anthropic_tc = None
        if anthropic_tools:
            if tool_choice is None or tool_choice == "auto":
                anthropic_tc = {"type": "auto"}
            elif isinstance(tool_choice, dict) and tool_choice.get("type") == "function":
                anthropic_tc = {"type": "tool", "name": tool_choice["function"]["name"]}
            elif tool_choice == "none":
                anthropic_tools = None

        kwargs = {
            "model": self.model,
            "messages": anthropic_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        if anthropic_tc:
            kwargs["tool_choice"] = anthropic_tc

        start = time.time()
        response = self._anthropic_client.messages.create(**kwargs)
        elapsed = time.time() - start

        content = None
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ChatCompletionMessageToolCall(
                        id=block.id,
                        type="function",
                        function=Function(
                            name=block.name,
                            arguments=json.dumps(block.input, ensure_ascii=False),
                        ),
                    )
                )

        msg = ChatCompletionMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls if tool_calls else None,
        )
        self._track_usage(
            response.usage.input_tokens,
            response.usage.output_tokens,
            elapsed, tag, msg,
        )
        return msg

    @staticmethod
    def _translate_messages(messages):
        """OpenAI message list -> Anthropic (system, messages)."""
        system_parts = []
        result = []

        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg["role"]

            if role == "system":
                system_parts.append(msg["content"])
                i += 1

            elif role == "user":
                result.append({"role": "user", "content": msg["content"]})
                i += 1

            elif role == "assistant":
                blocks = []
                if msg.get("content"):
                    blocks.append({"type": "text", "text": msg["content"]})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        args = tc["function"]["arguments"]
                        blocks.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(args) if isinstance(args, str) else args,
                        })
                if not blocks:
                    blocks.append({"type": "text", "text": ""})
                result.append({"role": "assistant", "content": blocks})
                i += 1

            elif role == "tool":
                tool_results = []
                while i < len(messages) and messages[i]["role"] == "tool":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": messages[i]["tool_call_id"],
                        "content": messages[i]["content"] or "",
                    })
                    i += 1
                result.append({"role": "user", "content": tool_results})

            else:
                i += 1

        system = "\n\n".join(system_parts) if system_parts else None
        return system, result

    # ---- shared ----

    def _track_usage(self, prompt_tokens, completion_tokens, elapsed, tag, msg):
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_calls += 1
        total = prompt_tokens + completion_tokens
        label = f"[LLM:{tag}]" if tag else "[LLM]"
        logger.info(
            "%s 响应: %.1fs, tokens=%d(in:%d+out:%d)",
            label, elapsed, total, prompt_tokens, completion_tokens,
        )
        logger.debug("%s 输出: %.500s", label, msg.content)


if __name__ == "__main__":
    try:
        agent = LLMClient()

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that writes Python code.",
            },
            {"role": "user", "content": "请告诉我openai的SDK的常用代码和语法"},
        ]

        print("--- 调用LLM ---")
        response = agent.invoke(messages)
        if response:
            print("\n\n--- 完整模型响应 ---")
            print(response)

    except ValueError as e:
        print(e)
