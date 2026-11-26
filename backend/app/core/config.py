"""Central configuration management for Chanakya Research Commons."""
from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Chanakya Research Commons"
    APP_ENV: str = "development"
    DEBUG: bool = True
    ENABLE_SCHEDULER: bool = True

    DATABASE_URL: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'chanakya_commons.db').as_posix()}"

    JWT_SECRET_KEY: str = "chanakya-research-commons-local-dev-secret-key-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ROOT_USER: str = "chanakya_minio"
    MINIO_ROOT_PASSWORD: str = "chanakya_minio_pass"
    MINIO_BUCKET_RAW: str = "chanakya-raw-lake"
    MINIO_ENABLED: bool = False

    DATA_DIR: str = str(PROJECT_ROOT / "data")
    RAW_DATA_DIR: str = str(PROJECT_ROOT / "data" / "raw")
    PROCESSED_DATA_DIR: str = str(PROJECT_ROOT / "data" / "processed")
    PARQUET_DIR: str = str(PROJECT_ROOT / "data" / "parquet")
    DUCKDB_PATH: str = str(PROJECT_ROOT / "data_warehouse" / "duckdb" / "chanakya_dw.duckdb")

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    RANDOM_SEED: int = 42

    OPENALEX_MAILTO: str = "research-commons@chanakyauniversity.edu.in"
    ARXIV_RATE_LIMIT_SECONDS: float = 3.0
    SEMANTIC_SCHOLAR_API_KEY: str = ""

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    def validate_production_security(self) -> None:
        """Fail fast in production if insecure default secrets, DB config, or CORS remain configured."""
        if not self.is_production:
            return
        insecure_jwt_values = {
            "",
            "chanakya-research-commons-local-dev-secret-key-2026",
            "chanakya-docker-secret-key-change-me-32chars",
            "change-this-to-a-strong-random-32-char-secret-key",
            "replace-with-64-char-random-hex-secret",
        }
        if self.JWT_SECRET_KEY in insecure_jwt_values or len(self.JWT_SECRET_KEY) < 32:
            raise RuntimeError(
                "Production startup blocked: JWT_SECRET_KEY must be set to a strong random secret (>=32 chars)."
            )
        if not self.is_postgres:
            raise RuntimeError(
                "Production startup blocked: DATABASE_URL must point to PostgreSQL, not SQLite."
            )
        if "chanakya_dev_pass" in self.DATABASE_URL or "replace-with-" in self.DATABASE_URL:
            raise RuntimeError(
                "Production startup blocked: DATABASE_URL still contains a default/placeholder password."
            )
        if self.MINIO_ENABLED and (
            self.MINIO_ROOT_PASSWORD
            in {"", "chanakya_minio_pass", "minioadmin", "replace-with-strong-minio-password"}
            or len(self.MINIO_ROOT_PASSWORD) < 12
        ):
            raise RuntimeError(
                "Production startup blocked: MINIO_ROOT_PASSWORD must be changed from the development default."
            )
        if self.DEBUG:
            raise RuntimeError("Production startup blocked: DEBUG must be false when APP_ENV=production.")
        if not self.cors_origin_list or any(o == "*" for o in self.cors_origin_list):
            raise RuntimeError(
                "Production startup blocked: CORS_ORIGINS must specify explicit allowed origin(s) without '*'."
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
