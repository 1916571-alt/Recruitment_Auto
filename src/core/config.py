from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    """애플리케이션 설정 (환경변수 로드)"""
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    jobs_json_path: Path = Path("data/jobs.json")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_config() -> Settings:
    """설정 인스턴스 반환"""
    return Settings()
