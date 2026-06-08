import os


class Config:
    default_model: str = "GLM-4-Flash"
    default_provider: str = "glm"
    max_history_len: int = 100
    temperature: float = 0.7
    max_tokens: int | None = None

    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls):
        return cls(
            default_model=os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo"),
            default_provider=os.getenv("DEFAULT_PROVIDER", "openai"),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
        )

    def to_dict(self):
        return self.model_dump()