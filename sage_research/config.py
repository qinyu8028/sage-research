from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    model: str = "GLM-4-Flash"
    temperature: float = 0.0
    timeout: int = 120


@dataclass
class ContextConfig:
    max_tokens: int = 30000
    reserve_ratio: float = 0.15


@dataclass
class CompactorConfig:
    max_messages: int = 20
    keep_front_messages: int = 3
    max_tool_calls: int = 3
    max_tokens: int = 20000


@dataclass
class Config:
    config_dir: str = "configs"
    data_dir: str = "data"
    max_rounds: int = 3
    max_steps: int = 3
    llm: LLMConfig = field(default_factory=LLMConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    compactor: CompactorConfig = field(default_factory=CompactorConfig)
