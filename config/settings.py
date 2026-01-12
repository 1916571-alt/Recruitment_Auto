"""
채용 정보 수집 에이전트 설정
"""
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel


# =============================================================================
# Google Search 직군별 검색 쿼리
# =============================================================================
# 각 직군별로 신입/주니어 타겟 검색어를 정의합니다.
# API 무료 티어: 100회/일, 현재 약 16회 사용 예상

GOOGLE_SEARCH_QUERIES: Dict[str, List[str]] = {
    # 데이터 분석 직군
    "data": [
        "데이터 분석가 신입 채용",
        "Data Analyst 주니어 채용",
        "BI 분석가 신입 채용",
        "비즈니스 분석가 경력무관",
    ],
    # 프론트엔드 개발 직군
    "frontend": [
        "프론트엔드 개발자 신입 채용",
        "Frontend Developer 주니어",
        "React 개발자 신입 채용",
        "웹 퍼블리셔 신입 채용",
    ],
    # 백엔드 개발 직군
    "backend": [
        "백엔드 개발자 신입 채용",
        "Backend Developer 주니어",
        "서버 개발자 신입 채용",
        "Java 개발자 신입 채용",
    ],
    # 기획 직군
    "pm": [
        "서비스 기획자 신입 채용",
        "PM 주니어 채용",
        "프로덕트 매니저 신입",
        "IT 기획자 경력무관 채용",
    ],
}

# 활성화할 직군 목록 (빈 리스트면 전체 활성화)
ACTIVE_JOB_TYPES: List[str] = ["data", "frontend", "backend", "pm"]


class FilterSettings(BaseModel):
    """필터링 설정"""
    # 직무 키워드 (OR 조건) - 모든 직군 포함
    job_keywords: List[str] = [
        # 데이터 분석
        "데이터 분석", "데이터분석", "Data Analyst", "Data Analysis",
        "데이터 사이언티스트", "Data Scientist", "BI 분석", "비즈니스 분석",
        "데이터 엔지니어", "Data Engineer", "머신러닝", "ML Engineer",
        # 백엔드 개발
        "백엔드", "Backend", "서버 개발", "Server Developer",
        "Java 개발", "Spring", "Python 개발", "Node.js",
        # 프론트엔드 개발
        "프론트엔드", "Frontend", "React", "Vue", "웹 개발", "퍼블리셔",
        # PM/기획
        "서비스 기획", "PM", "프로덕트 매니저", "Product Manager",
        "IT 기획", "프로덕트 오너", "PO",
    ]

    # 제외 키워드 (타이틀에 이 키워드가 포함되면 제외)
    exclude_keywords: List[str] = [
        "시니어",
        "Senior",
        "팀장",
        "리드",
        "Lead",
        "Principal",
        "Staff",
        "Head",
    ]


class CrawlerSettings(BaseModel):
    """크롤러 설정"""
    # 크롤링 간격 (분)
    crawl_interval_minutes: int = 60

    # 요청 간 대기 시간 (초)
    request_delay_seconds: float = 2.0

    # 타임아웃 (초)
    request_timeout: int = 30

    # User-Agent
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


class DatabaseSettings(BaseModel):
    """데이터베이스 설정"""
    db_path: Path = Path("data/jobs.db")


class WebSettings(BaseModel):
    """웹 서버 설정"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


class Settings(BaseModel):
    """전체 설정"""
    filter: FilterSettings = FilterSettings()
    crawler: CrawlerSettings = CrawlerSettings()
    database: DatabaseSettings = DatabaseSettings()
    web: WebSettings = WebSettings()

    # 프로젝트 루트 경로
    base_dir: Path = Path(__file__).parent.parent


# 전역 설정 인스턴스
settings = Settings()
