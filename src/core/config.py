"""
애플리케이션 설정 관리

환경변수 기반 설정과 기본값을 통합 관리합니다.
"""
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class FilterConfig(BaseModel):
    """필터링 설정"""

    job_keywords: List[str] = Field(
        default=[
            "데이터 분석",
            "데이터분석",
            "Data Analyst",
            "Data Analysis",
            "데이터 사이언티스트",
            "Data Scientist",
            "BI 분석",
            "비즈니스 분석",
            "데이터 엔지니어",
            "Data Engineer",
            "머신러닝",
            "ML Engineer",
        ],
        description="포함할 직무 키워드 (OR 조건)",
    )

    exclude_keywords: List[str] = Field(
        default=[
            "시니어",
            "Senior",
            "팀장",
            "리드",
            "Lead",
            "Principal",
            "Staff",
            "Head",
        ],
        description="제외할 키워드",
    )

    entry_level_keywords: List[str] = Field(
        default=[
            "신입",
            "경력무관",
            "경력 무관",
            "인턴",
            "intern",
            "entry",
            "junior",
            "신입/경력",
            "경력/신입",
        ],
        description="신입 가능 키워드",
    )


class CrawlerConfig(BaseModel):
    """크롤러 설정"""

    request_delay_seconds: float = Field(
        default=2.0,
        description="요청 간 대기 시간 (초)",
    )

    request_timeout: int = Field(
        default=30,
        description="요청 타임아웃 (초)",
    )

    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        description="User-Agent 헤더",
    )

    max_detail_fetch: int = Field(
        default=5,
        description="상세 정보를 가져올 최대 공고 수",
    )


class ExporterConfig(BaseModel):
    """내보내기 설정"""

    new_threshold_hours: int = Field(
        default=48,
        description="새 공고 판정 시간 (시간)",
    )


class ApiConfig(BaseModel):
    """외부 API 설정"""

    perplexity_api_key: Optional[str] = Field(
        default=None,
        description="Perplexity API 키",
    )

    google_api_key: Optional[str] = Field(
        default=None,
        description="Google API 키",
    )

    google_cse_id: Optional[str] = Field(
        default=None,
        description="Google Custom Search Engine ID",
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API 키 (임베딩용)",
    )


class AppConfig(BaseSettings):
    """애플리케이션 전체 설정

    환경변수에서 값을 읽어옵니다:
    - PERPLEXITY_API_KEY
    - GOOGLE_API_KEY
    - GOOGLE_CSE_ID
    - OPENAI_API_KEY
    - GROQ_API_KEY
    """

    # 서브 설정
    filter: FilterConfig = Field(default_factory=FilterConfig)
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    exporter: ExporterConfig = Field(default_factory=ExporterConfig)

    # API 키 (환경변수에서 로드)
    perplexity_api_key: Optional[str] = Field(default=None, alias="PERPLEXITY_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    google_cse_id: Optional[str] = Field(default=None, alias="GOOGLE_CSE_ID")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", description="Groq 모델 ID")
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")

    # 경로 설정
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)

    @property
    def data_dir(self) -> Path:
        """데이터 디렉토리 경로"""
        return self.base_dir / "data"

    @property
    def docs_dir(self) -> Path:
        """문서 디렉토리 경로 (GitHub Pages)"""
        return self.base_dir / "docs"

    @property
    def jobs_json_path(self) -> Path:
        """jobs.json 경로"""
        return self.data_dir / "jobs.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 싱글톤 인스턴스
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """설정 인스턴스 반환 (싱글톤)"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reset_config() -> None:
    """설정 인스턴스 리셋 (테스트용)"""
    global _config
    _config = None
