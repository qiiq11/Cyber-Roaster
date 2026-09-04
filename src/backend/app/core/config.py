"""应用配置。

所有配置均通过环境变量注入，便于在本地、Docker 与 CI 环境间无缝切换。
环境变量清单见仓库根目录的 `.env.example`。
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置模型。

    字段名与 `.env.example` 中的变量一一对应。
    """

    # --- 应用基础信息 ---
    app_name: str = "Cyber-Roaster"
    app_version: str = "1.0.0"
    debug: bool = False

    # --- LLM（OpenAI 兼容 API）---
    # 支持硅基流动 / Azure OpenAI / DeepSeek 等任意 OpenAI 兼容端点。
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.siliconflow.cn/v1"
    openai_model: str = "deepseek-ai/DeepSeek-V3"
    llm_timeout_seconds: float = 60.0
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.9

    # --- GitHub 集成 ---
    github_token: Optional[str] = None
    github_api_base: str = "https://api.github.com"
    webhook_secret: Optional[str] = None

    # --- 数据库 ---
    database_url: str = "sqlite:///./cyber_roaster.db"

    # --- 梗图生成 ---
    # 梗图模板偏好：memegen（默认，调用免费 memegen.link API）或 pillow（本地自绘）。
    meme_template_preference: str = "memegen"

    # --- 限流 ---
    rate_limit_default: str = "60/minute"
    rate_limit_llm: str = "20/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """返回缓存的配置单例，避免重复读取环境变量。"""
    return Settings()
