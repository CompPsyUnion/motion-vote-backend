from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/motionvote"
    test_database_url: str = "postgresql://postgres:password@localhost:5432/motionvote_test"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Email
    smtp_tls: bool = True
    smtp_port: int = 587
    smtp_host: str = "smtp.gmail.com"
    smtp_user: str = ""
    smtp_password: str = ""

    # Application
    app_name: str = "Motion Vote API"
    app_version: str = "1.0.0"
    debug: bool = True
    cors_origins: List[str] = [
        "http://localhost:3000", "http://localhost:5173"]

    # File Upload
    upload_dir: str = "uploads"
    max_file_size: int = 10485760  # 10MB

    # WebSocket
    ws_heartbeat_interval: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
