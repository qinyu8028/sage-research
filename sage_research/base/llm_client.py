import os
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from dotenv import load_dotenv

load_dotenv()

MODEL_PROFILES = {
    "glm": {
        "api_key": "GLM_API_KEY",
        "base_url": "GLM_BASE_URL",
    },
    "deepseek": {
        "api_key": "DEEPSEEK_API_KEY",
        "base_url": "DEEPSEEK_BASE_URL",
        "extra_body": {"thinking": {"type": "disabled"}},
    },
}


def _resolve_model_env(model: str) -> tuple[str, str, dict | None]:
    supported = list(MODEL_PROFILES.keys())
    for prefix, profile in MODEL_PROFILES.items():
        if model.lower().startswith(prefix):
            env_keys = {k: v for k, v in profile.items() if k not in ("extra_body",)}
            missing = [v for v in env_keys.values() if not os.getenv(v)]
            if missing:
                raise ValueError(
                    f"模型 '{model}' 匹配到 '{prefix}'，"
                    f"但以下环境变量未设置: {', '.join(missing)}"
                )
            return (
                os.getenv(profile["api_key"]),
                os.getenv(profile["base_url"]),
                profile.get("extra_body"),
            )
    raise ValueError(
        f"未知模型 '{model}'，支持的前缀: {supported}。"
        f"请在 MODEL_PROFILES 中添加配置，或显式传入 api_key/base_url。"
    )


class TestAgent:
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

        if api_key and base_url:
            self.api_key, self.base_url, self.extra_body = api_key, base_url, None
        else:
            resolved_key, resolved_url, extra_body = _resolve_model_env(self.model)
            self.api_key = api_key or resolved_key
            self.base_url = base_url or resolved_url
            self.extra_body = extra_body

        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        self.client = OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

    def invoke(
        self, messages: list[dict[str, str]], temperature: float = 0, tools=None, tool_choice=None
    ) -> ChatCompletionMessage:
        print(f"🧠 正在调用 {self.model} 模型...")

        if tool_choice is None:
            tool_choice = "auto" if tools else None

        kwargs = dict(
            messages=messages,
            model=self.model,
            temperature=temperature,
            tool_choice=tool_choice,
            tools=tools if tools else None,
        )
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body

        response = self.client.chat.completions.create(**kwargs)
        
        return response.choices[0].message


if __name__ == "__main__":
    try:
        agent = TestAgent()

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
