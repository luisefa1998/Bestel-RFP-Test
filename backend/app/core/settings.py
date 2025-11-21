from pydantic_settings import BaseSettings
from typing import List, Optional, Literal
import os
from pathlib import Path

# Get the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Logging mode type
LoggingMode = Literal["none", "all", "errors", "workflows"]


class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Document Processing API"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    
    # Project settings
    PROJECTS_DIR: Path = BASE_DIR.parent / "data" / "projects"
    
    # Milvus Cloud settings
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "")
    MILVUS_PORT: str = os.getenv("MILVUS_PORT", "")
    MILVUS_USER: str = os.getenv("MILVUS_USER", "")
    MILVUS_KEY: str = os.getenv("MILVUS_KEY", "")
    
    # Embedding settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", 0))
    # Tokenizer model for chunking (HuggingFace compatible)
    # Should match the embedding model's tokenizer
    TOKENIZER_MODEL: str = os.getenv("TOKENIZER_MODEL", "")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
    
    # Celery settings
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    CELERY_QUEUE_NAME: str = os.getenv("CELERY_QUEUE_NAME", "celery")

    # WatsonX settings
    WX_API_KEY: str = os.getenv("WX_API_KEY", "")
    WX_PROJECT_ID: str = os.getenv("WX_PROJECT_ID", "")
    
    # Logging settings
    # Can be set via environment variable or command-line argument
    # Options: "none" (console only), "all" (all logs to files), "errors" (only errors to file), "workflows" (only workflow logs to file), "tasks" (only task logs to file)
    LOGGING_MODE: str = "none"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate logging mode
        valid_modes = ["none", "all", "errors", "workflows", "tasks"]
        if self.LOGGING_MODE not in valid_modes:
            raise ValueError(f"LOGGING_MODE must be one of {valid_modes}, got: {self.LOGGING_MODE}")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


# Create settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.PROJECTS_DIR, exist_ok=True)
