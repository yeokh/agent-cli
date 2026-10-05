"""Environment-driven gateway settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _normalize_base_url(url: str) -> str:
    """Strip trailing slashes and a trailing /v1 so callers can pass either form."""
    base = url.rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return base.rstrip("/")


@dataclass(frozen=True)
class Settings:
    upstream_base_url: str = "https://openrouter.ai/api"
    upstream_api_key: str = ""
    listen_host: str = "0.0.0.0"
    listen_port: int = 8009
    default_model: str = "jev-latest"
    gateway_api_key: str = ""
    upstream_timeout_s: float = 60.0
    curated_models: tuple[str, ...] = field(
        default_factory=lambda: (
            "jev-latest",
            "jev-1.13",
            "typesafe/jev-1.13",
            "typesafe/jev-latest",
            "kev-latest",
            "nimble",
            "laya",
            "laya-multilingual",
            "laya-english",
            "laya-typed-decisions",
        )
    )

    @property
    def upstream_origin(self) -> str:
        return _normalize_base_url(self.upstream_base_url)

    @property
    def systemone_url(self) -> str:
        return f"{self.upstream_origin}/v1/systemone"

    @property
    def models_url(self) -> str:
        return f"{self.upstream_origin}/v1/models"

    @classmethod
    def from_env(cls) -> Settings:
        curated = os.getenv("CURATED_MODELS", "").strip()
        models = (
            tuple(m.strip() for m in curated.split(",") if m.strip())
            if curated
            else cls().curated_models
        )
        return cls(
            upstream_base_url=os.getenv(
                "UPSTREAM_BASE_URL", "https://openrouter.ai/api"
            ),
            upstream_api_key=os.getenv("UPSTREAM_API_KEY", ""),
            listen_host=os.getenv("LISTEN_HOST", "0.0.0.0"),
            listen_port=int(os.getenv("LISTEN_PORT", "8009")),
            default_model=os.getenv("DEFAULT_MODEL", "jev-latest"),
            gateway_api_key=os.getenv("GATEWAY_API_KEY", ""),
            upstream_timeout_s=float(os.getenv("UPSTREAM_TIMEOUT_S", "60")),
            curated_models=models,
        )


settings = Settings.from_env()
