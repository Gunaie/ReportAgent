"""全局配置 — 基于 Pydantic Settings 管理环境变量。"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，自动从 .env 文件加载。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # === LLM 配置 ===
    dashscope_api_key: str = "sk-xxx"
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    flash_model: str = "deepseek-v4-flash"
    pro_model: str = "deepseek-v4-pro"

    # === 搜索 ===
    tavily_api_key: str = ""

    # === 数据库 ===
    database_url: str = "sqlite+aiosqlite:///./data/reports.db"

    # === 输出目录 ===
    output_dir: str = "./outputs"

    @property
    def output_md_dir(self) -> Path:
        return Path(self.output_dir) / "md"


# 全局单例
settings = Settings()
