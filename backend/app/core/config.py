from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)
    
    app_name: str = "dep-health"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    database_url: Optional[str] = None
    
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "dep_health"
    
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    github_token: Optional[str] = None
    github_api_url: str = "https://api.github.com"
    
    nvd_api_key: Optional[str] = None
    nvd_api_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    
    osv_api_url: str = "https://api.osv.dev/v1"
    
    npm_registry_url: str = "https://registry.npmjs.org"
    maven_central_url: str = "https://search.maven.org/solrsearch/select"
    pypi_url: str = "https://pypi.org/pypi"
    docker_hub_url: str = "https://hub.docker.com/v2"
    
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"
    
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    ml_model_path: str = "/app/models"
    data_dir: str = "/app/data"
    
    github_webhook_secret: Optional[str] = None
    
    log_level: str = "INFO"
    log_format: str = "json"
    
    cors_origins: list[str] = ["http://localhost:3000", "https://dephealth.vercel.app"]
    
    prometheus_port: int = 9090


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()