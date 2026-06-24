import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    model: str = os.getenv("LLM_MODEL_ID", "deepseek-v4-flash")
    temperature: float = 0.0
    research_temperature: float = 0.6
    writer_temperature: float = 0.3
    timeout: int = 120


@dataclass
class ContextConfig:
    max_tokens: int = 30000
    reserve_ratio: float = 0.15


@dataclass
class Config:
    config_dir: str = "configs"
    data_dir: str = "data"
    max_rounds: int = 3
    max_steps: int = 3
    llm: LLMConfig = field(default_factory=LLMConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
