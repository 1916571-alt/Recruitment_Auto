"""
프로필-채용공고 매칭 서비스

단일 책임: 프로필과 채용 공고의 매칭 점수 계산
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from src.core.interfaces import MatcherProtocol
from src.models.job import JobPosting
from src.models.profile import Profile, JobCategory
from src.models.match import MatchResult, ScoreBreakdown


# 직무 카테고리 키워드 매핑
CATEGORY_KEYWORDS: Dict[JobCategory, List[str]] = {
    JobCategory.DATA: [
        "데이터 분석", "data analyst", "데이터 사이언", "ml engineer",
        "머신러닝", "bi 분석", "데이터 엔지니어", "빅데이터", "ai",
    ],
    JobCategory.BACKEND: [
        "백엔드", "backend", "서버 개발", "java", "python", "node.js",
        "spring", "django", "fastapi", "go", "kotlin",
    ],
    JobCategory.FRONTEND: [
        "프론트엔드", "frontend", "react", "vue", "angular", "웹 개발",
        "퍼블리셔", "javascript", "typescript", "next.js",
    ],
    JobCategory.FULLSTACK: [
        "풀스택", "full stack", "fullstack", "웹 개발자",
    ],
    JobCategory.PM: [
        "기획", "pm", "po", "product", "서비스 기획", "프로덕트", "프로젝트 매니저",
    ],
    JobCategory.DESIGN: [
        "디자인", "ui/ux", "ux", "프로덕트 디자이너", "그래픽", "figma",
    ],
}


class ProfileMatcher(MatcherProtocol):
    """프로필 매칭 서비스

    2-Stage 매칭:
    1단계: 경력 조건 필터 (통과 못하면 제외)
    2단계: 직무 카테고리 + 스킬/설명 유사도 점수
    """

    # 점수 가중치 (2단계)
    CATEGORY_WEIGHT = 40  # 직무 카테고리 매칭
    EMBEDDING_WEIGHT = 60  # 스킬/설명 유사도

    # 매칭 임계값
    MIN_SCORE_THRESHOLD = 40
    TOP_K_RESULTS = 10

    def calculate_score(
        self,
        profile_embedding: List[float],
        job_embedding: List[float]
    ) -> float:
        """코사인 유사도 계산 (0-100)"""
        a = np.array(profile_embedding)
        b = np.array(job_embedding)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        similarity = np.dot(a, b) / (norm_a * norm_b)
        return float(similarity * 100)

    def match_profile_to_jobs(
        self,
        profile: Profile,
        jobs: List[JobPosting],
        job_embeddings: Dict[str, List[float]],
    ) -> List[MatchResult]:
        """프로필과 모든 채용 공고 매칭 (2-Stage)

        Args:
            profile: 사용자 프로필
            jobs: 채용 공고 리스트
            job_embeddings: 채용 공고 ID별 임베딩

        Returns:
            매칭 결과 리스트 (점수 내림차순)
        """
        results = []

        for job in jobs:
            # ========================================
            # 1단계: 경력 조건 필터 (Hard Filter)
            # ========================================
            if not self._matches_experience(profile.experience_years, job):
                continue  # 경력 조건 불일치 시 완전 제외

            # ========================================
            # 2단계: 직무 카테고리 + 스킬/설명 유사도
            # ========================================
            score_breakdown = ScoreBreakdown()

            # 직무 카테고리 매칭 (40점)
            job_text = f"{job.title} {job.description or ''}".lower()
            keywords = CATEGORY_KEYWORDS.get(profile.job_category, [])
            if any(kw.lower() in job_text for kw in keywords):
                score_breakdown.category_score = self.CATEGORY_WEIGHT

            # 임베딩 유사도 (60점)
            if profile.embedding and job.id in job_embeddings:
                raw_similarity = self.calculate_score(
                    profile.embedding,
                    job_embeddings[job.id]
                )
                # 0-100 유사도를 0-60 점수로 변환
                embedding_score = raw_similarity * (self.EMBEDDING_WEIGHT / 100)
                score_breakdown.embedding_score = embedding_score

            total_score = (
                score_breakdown.category_score +
                score_breakdown.embedding_score
            )

            if total_score >= self.MIN_SCORE_THRESHOLD:
                # 스킬 분석 (부족한 스킬만 사용)
                _, missing_skills = self._analyze_skills(
                    profile.skills,
                    job.tech_stack or []
                )

                results.append(MatchResult(
                    profile_id=profile.id,
                    job_id=job.id,
                    total_score=round(total_score, 1),
                    score_breakdown=score_breakdown,
                    matched_skills=[],  # 사용하지 않음
                    missing_skills=missing_skills,
                ))

        # 점수 내림차순 정렬, 상위 K개
        results.sort(key=lambda x: x.total_score, reverse=True)
        return results[:self.TOP_K_RESULTS]

    def _calculate_rule_score(
        self,
        profile: Profile,
        job: JobPosting
    ) -> ScoreBreakdown:
        """규칙 기반 점수 계산"""
        breakdown = ScoreBreakdown()

        # 1. 직무 카테고리 점수
        job_text = f"{job.title} {job.description or ''}".lower()
        keywords = CATEGORY_KEYWORDS.get(profile.job_category, [])

        if any(kw.lower() in job_text for kw in keywords):
            breakdown.category_score = self.CATEGORY_WEIGHT

        # 2. 경력 조건 점수
        if self._matches_experience(profile.experience_years, job):
            breakdown.experience_score = self.EXPERIENCE_WEIGHT

        # 3. 위치 조건 점수
        if self._matches_location(profile.preferred_locations, job.location):
            breakdown.location_score = self.LOCATION_WEIGHT

        return breakdown

    def _matches_experience(self, years: int, job: JobPosting) -> bool:
        """경력 조건 매칭"""
        exp_level = str(job.experience_level).lower() if job.experience_level else ""
        exp_text = (job.experience_text or "").lower()

        # 신입
        if years == 0:
            return any(kw in exp_text or kw in exp_level for kw in [
                "신입", "경력무관", "인턴", "entry", "junior", "주니어"
            ])

        # 경력자는 대부분 매칭
        return True

    def _matches_location(
        self,
        preferred: List[str],
        job_location: Optional[str]
    ) -> bool:
        """위치 조건 매칭"""
        if not preferred or not job_location:
            return True

        job_loc = job_location.lower()
        return any(loc.lower() in job_loc for loc in preferred)

    def _analyze_skills(
        self,
        profile_skills: List[str],
        job_skills: List[str]
    ) -> Tuple[List[str], List[str]]:
        """스킬 매칭 분석"""
        profile_set = {s.lower() for s in profile_skills}
        job_set = {s.lower() for s in job_skills}

        matched = [s for s in job_skills if s.lower() in profile_set]
        missing = [s for s in job_skills if s.lower() not in profile_set]

        return matched, missing


def format_match_comment(
    profile: Profile,
    matches: List[MatchResult],
    jobs_map: Dict[str, JobPosting],
) -> str:
    """매칭 결과를 GitHub Issue 코멘트용 마크다운으로 포맷팅

    Args:
        profile: 사용자 프로필
        matches: 매칭 결과 리스트
        jobs_map: job_id -> JobPosting 매핑

    Returns:
        마크다운 포맷 문자열
    """
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"## 추천 채용 공고 ({today})",
        "",
        f"**{len(matches)}건**의 채용 공고가 프로필과 매칭되었습니다.",
        "",
    ]

    if not matches:
        lines.append("> 현재 매칭된 공고가 없습니다. 프로필 정보를 업데이트하거나 잠시 후 다시 확인해주세요.")
        return "\n".join(lines)

    # 매칭 결과 테이블
    lines.extend([
        "| 회사 | 포지션 | 매칭률 | 마감 | 링크 |",
        "|------|--------|--------|------|------|",
    ])

    for match in matches:
        job = jobs_map.get(match.job_id)
        if not job:
            continue

        # 마감일 표시
        deadline_str = "상시"
        if job.deadline_text:
            deadline_str = job.deadline_text
        elif job.deadline:
            days_left = (job.deadline - datetime.now()).days
            if days_left >= 0:
                deadline_str = f"D-{days_left}"
            else:
                deadline_str = "마감"

        # 매칭률
        score_str = f"{match.total_score:.0f}%"

        # 테이블 행 추가
        lines.append(
            f"| {job.company_name} | {job.title} | {score_str} | {deadline_str} | [지원하기]({job.source_url}) |"
        )

    # 보완하면 좋을 기술 (상위 3개 공고 기준)
    all_missing_skills = []
    for match in matches[:3]:
        all_missing_skills.extend(match.missing_skills)

    if all_missing_skills:
        unique_missing = list(dict.fromkeys(all_missing_skills))[:5]
        lines.extend([
            "",
            "### 보완하면 좋을 기술",
            f"> {', '.join(unique_missing)}",
        ])

    lines.extend([
        "",
        "---",
        "*자동 생성됨 by Recruitment Auto*",
    ])

    return "\n".join(lines)
