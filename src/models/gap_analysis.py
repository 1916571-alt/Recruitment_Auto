"""
갭 분석 및 커리어 조언 모델

프로필과 채용 공고 비교 결과 및 LLM 기반 커리어 조언을 정의합니다.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SkillGapLevel(str, Enum):
    """스킬 갭 수준"""
    CRITICAL = "critical"      # 필수 기술 미보유
    IMPORTANT = "important"    # 중요 기술 미보유
    NICE_TO_HAVE = "nice_to_have"  # 우대 기술 미보유


class SkillGap(BaseModel):
    """부족한 스킬 정보"""
    skill_name: str = Field(..., description="기술명")
    gap_level: SkillGapLevel = Field(..., description="갭 수준")
    frequency: float = Field(0.0, description="채용 공고에서 등장 비율 (0-1)")
    learning_priority: int = Field(1, description="학습 우선순위 (1=최우선)")
    suggested_resources: List[str] = Field(default_factory=list, description="학습 리소스")


class SkillMatch(BaseModel):
    """매칭된 스킬 정보"""
    skill_name: str = Field(..., description="기술명")
    proficiency_level: Optional[str] = Field(None, description="숙련도")
    is_highlight: bool = Field(False, description="자기소개서 강조 추천")


class GapAnalysisResult(BaseModel):
    """갭 분석 결과"""
    profile_id: str = Field(..., description="프로필 Issue ID")
    job_ids: List[str] = Field(default_factory=list, description="분석 대상 채용 공고 ID")

    # 스킬 분석
    matched_skills: List[SkillMatch] = Field(default_factory=list, description="매칭된 기술")
    skill_gaps: List[SkillGap] = Field(default_factory=list, description="부족한 기술")

    # 요약 통계
    total_jobs_analyzed: int = Field(0, description="분석된 채용 공고 수")
    match_coverage: float = Field(0.0, description="필수 기술 충족률 (0-100)")

    # 주요 인사이트
    top_missing_skills: List[str] = Field(default_factory=list, description="가장 부족한 기술 Top 5")
    recommended_certifications: List[str] = Field(default_factory=list, description="추천 자격증")

    # 메타
    analyzed_at: datetime = Field(default_factory=datetime.now)


class LearningResource(BaseModel):
    """학습 리소스"""
    name: str = Field(..., description="리소스 이름")
    type: str = Field(..., description="유형 (강의/책/프로젝트)")
    url: Optional[str] = Field(None, description="URL")
    estimated_duration: Optional[str] = Field(None, description="예상 소요 기간")


class LearningRoadmapItem(BaseModel):
    """학습 로드맵 항목"""
    week: int = Field(..., description="주차 (1부터 시작)")
    skill: str = Field(..., description="학습할 기술")
    goal: str = Field(..., description="주간 목표")
    resources: List[LearningResource] = Field(default_factory=list)


class PortfolioSuggestion(BaseModel):
    """포트폴리오 프로젝트 제안"""
    project_idea: str = Field(..., description="프로젝트 아이디어")
    skills_demonstrated: List[str] = Field(default_factory=list, description="증명할 기술")
    difficulty: str = Field("중", description="난이도 (하/중/상)")
    estimated_duration: str = Field(..., description="예상 소요 기간")


class ResumeKeyword(BaseModel):
    """자기소개서 추천 키워드"""
    keyword: str = Field(..., description="키워드")
    context: str = Field(..., description="사용 맥락 예시")
    frequency_in_jobs: float = Field(0.0, description="채용 공고 등장 비율")


class CareerAdvice(BaseModel):
    """LLM 생성 커리어 조언"""
    profile_id: str = Field(..., description="프로필 Issue ID")
    gap_analysis_id: Optional[str] = Field(None, description="연결된 갭 분석 ID")

    # 핵심 요약
    executive_summary: str = Field(..., description="핵심 요약 (2-3문장)")

    # 학습 로드맵
    learning_roadmap: List[LearningRoadmapItem] = Field(
        default_factory=list,
        description="주간 학습 로드맵 (12주)"
    )

    # 포트폴리오
    portfolio_suggestions: List[PortfolioSuggestion] = Field(
        default_factory=list,
        description="포트폴리오 프로젝트 제안"
    )

    # 자기소개서
    resume_keywords: List[ResumeKeyword] = Field(
        default_factory=list,
        description="자기소개서 추천 키워드"
    )

    # 전략적 조언
    short_term_actions: List[str] = Field(
        default_factory=list,
        description="단기 액션 아이템 (1개월)"
    )
    mid_term_goals: List[str] = Field(
        default_factory=list,
        description="중기 목표 (3개월)"
    )

    # 메타
    generated_at: datetime = Field(default_factory=datetime.now)
    llm_model: str = Field("llama-3.3-70b-versatile", description="사용된 LLM 모델")
