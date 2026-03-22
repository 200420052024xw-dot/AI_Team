import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


# 获取config目录的绝对路径
CONFIG_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "Skill Recommendation System"
    APP_VERSION: str = "1.0.0-lite"
    DEBUG: bool = True

    # API配置
    API_V1_PREFIX: str = "/api/v1"

    # 数据存储配置 (使用JSON文件)
    DATA_DIR: str = str(Path(__file__).resolve().parent.parent / "data")
    SKILLS_JSON: str = str(Path(__file__).resolve().parent.parent / "data" / "skills.json")

    # ChromaDB配置
    CHROMA_PERSIST_DIR: str = str(Path(__file__).resolve().parent.parent / "data" / "chromadb")
    SKILL_COLLECTION_NAME: str = "skill_embeddings"

    # 本地Embedding模型配置
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384

    # Anthropic API配置 (可选)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = "https://api.minimaxi.com/anthropic"
    CLAUDE_MODEL: str = "MiniMax-M2.7"

    # 检索配置
    DEFAULT_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.35
    RERANK_TOP_K: int = 20
    FINAL_TOP_K: int = 5

    class Config:
        env_file = str(CONFIG_DIR / ".env")
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
