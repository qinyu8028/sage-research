import os
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from dotenv import load_dotenv

load_dotenv()


class TestAgent:
    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        timeout: int = None,
    ):
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.api_key = api_key or os.getenv("GLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        if not all([self.model, self.api_key, self.base_url]):
            raise ValueError(
                "model_id, api_key and base_url have to be predefined or given."
            )

        self.client = OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

    def invoke(
        self, messages: list[dict[str, str]], temperature: float = 0, tools=None, tool_choice=None
    ) -> ChatCompletionMessage:
        print(f"🧠 正在调用 {self.model} 模型...")

        if tool_choice is None:
            tool_choice = "auto" if tools else None

        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=temperature,
            tool_choice=tool_choice,
            tools=tools if tools else None,
        )
        
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
