"""
프로필 모델

사용자 프로필 정보를 정의합니다.
GitHub Issue에서 파싱된 프로필 데이터를 저장합니다.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class JobCategory(str, Enum):
    """직무 카테고리"""
    DATA = "data"
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    PM = "pm"
    DESIGN = "design"
    SALES = "sales"  # 영업/영업관리


class Profile(BaseModel):
    """사용자 프로필 모델"""

    # 식별 정보
    id: str = Field(..., description="GitHub Issue ID (issue number)")
    github_username: str = Field(..., description="GitHub 사용자명")
    email: Optional[str] = Field(None, description="이메일 (뉴스레터용)")

    # 희망 조건
    job_category: JobCategory = Field(..., description="희망 직무")
    experience_years: int = Field(0, description="경력 연수 (0=신입)")
    preferred_locations: List[str] = Field(
        default_factory=list,
        description="희망 근무지"
    )

    # 역량
    skills: List[str] = Field(default_factory=list, description="보유 기술")
    certifications: List[str] = Field(default_factory=list, description="자격증")
    education: Optional[str] = Field(None, description="학력")
    portfolio_url: Optional[str] = Field(None, description="포트폴리오 URL")

    # 추가 설명
    introduction: Optional[str] = Field(None, description="자기소개")

    # 메타 정보
    issue_url: str = Field(..., description="GitHub Issue URL")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(True, description="활성 상태")

    # 임베딩 (런타임에 로드, JSON 직렬화에서 제외)
    embedding: Optional[List[float]] = Field(None, exclude=True)

    def to_embedding_text(self) -> str:
        """임베딩 생성용 텍스트 반환"""
        parts = [
            f"직무: {self.job_category.value}",
            f"경력: {self.experience_years}년",
            f"기술스택: {', '.join(self.skills)}",
        ]
        if self.certifications:
            parts.append(f"자격증: {', '.join(self.certifications)}")
        if self.introduction:
            parts.append(f"소개: {self.introduction}")
        return " | ".join(parts)
