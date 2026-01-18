"""
중복 채용 공고 탐지 서비스

Fuzzy Matching을 사용하여 여러 소스에서 수집된 중복 공고를 탐지하고,
정보가 더 풍부한 공고를 우선합니다.
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from loguru import logger
from rapidfuzz import fuzz

from src.models.job import JobPosting, JobSource


# =============================================================================
# 정규화 패턴
# =============================================================================

# 회사명에서 제거할 패턴
COMPANY_PATTERNS_TO_REMOVE = [
    r'\(주\)', r'주식회사', r'\(유\)', r'유한회사',
    r'Inc\.?', r'Corp\.?', r'Co\.?,?\s*Ltd\.?', r'Ltd\.?',
    r'LLC', r'GmbH', r'S\.A\.', r'PLC',
    r'㈜', r'㈜', r'\s+',
]

# 제목에서 제거할 패턴
TITLE_PATTERNS_TO_REMOVE = [
    r'\[.*?\]',  # [신입], [정규직] 등
    r'\(.*?\)',  # (신입), (정규직) 등
    r'채용', r'모집', r'구인', r'영입',
    r'신입', r'경력', r'경력무관', r'인턴',
    r'정규직', r'계약직', r'프리랜서',
    r'\s+',
]


@dataclass
class DuplicateGroup:
    """중복 공고 그룹"""
    primary: JobPosting  # 대표 공고 (정보가 가장 풍부한 것)
    duplicates: List[JobPosting]  # 중복으로 판정된 공고들
    similarity_scores: List[float]  # 유사도 점수


class JobDeduplicator:
    """채용 공고 중복 탐지기"""

    # 유사도 임계값
    COMPANY_THRESHOLD = 80  # 회사명 유사도 임계값 (%)
    TITLE_THRESHOLD = 70    # 제목 유사도 임계값 (%)

    # 소스 우선순위 (정보 품질 기준, 높을수록 우선)
    SOURCE_PRIORITY: Dict[JobSource, int] = {
        JobSource.WANTED: 100,       # 기술스택, 상세 설명 풍부
        JobSource.JUMPIT: 90,        # 개발자 특화, 기술스택 명시
        JobSource.ROCKETPUNCH: 80,   # 스타트업 정보 풍부
        JobSource.JOBKOREA: 70,      # 대기업 공고 많음
        JobSource.SARAMIN: 60,       # 일반 채용 정보
        JobSource.INTHISWORK: 50,    # 큐레이션
        JobSource.GOOGLE_SEARCH: 40, # 검색 결과
    }

    def __init__(
        self,
        company_threshold: int = 80,
        title_threshold: int = 70,
    ):
        self.company_threshold = company_threshold
        self.title_threshold = title_threshold
        self._company_cache: Dict[str, str] = {}
        self._title_cache: Dict[str, str] = {}

    def normalize_company_name(self, name: str) -> str:
        """회사명 정규화"""
        if name in self._company_cache:
            return self._company_cache[name]

        normalized = name.strip().lower()

        # 패턴 제거
        for pattern in COMPANY_PATTERNS_TO_REMOVE:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

        # 공백 정리
        normalized = re.sub(r'\s+', '', normalized)

        self._company_cache[name] = normalized
        return normalized

    def normalize_title(self, title: str) -> str:
        """제목 정규화"""
        if title in self._title_cache:
            return self._title_cache[title]

        normalized = title.strip().lower()

        # 패턴 제거
        for pattern in TITLE_PATTERNS_TO_REMOVE:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

        # 공백 정리
        normalized = re.sub(r'\s+', '', normalized)

        self._title_cache[title] = normalized
        return normalized

    def calculate_similarity(
        self,
        job1: JobPosting,
        job2: JobPosting
    ) -> Tuple[float, float]:
        """두 공고의 유사도 계산 (회사명, 제목)"""
        # 회사명 유사도
        company1 = self.normalize_company_name(job1.company_name)
        company2 = self.normalize_company_name(job2.company_name)
        company_sim = fuzz.ratio(company1, company2)

        # 제목 유사도 (token_set_ratio 사용 - 단어 순서 무관)
        title1 = self.normalize_title(job1.title)
        title2 = self.normalize_title(job2.title)
        title_sim = fuzz.token_set_ratio(title1, title2)

        return company_sim, title_sim

    def is_duplicate(self, job1: JobPosting, job2: JobPosting) -> bool:
        """두 공고가 중복인지 판정"""
        company_sim, title_sim = self.calculate_similarity(job1, job2)

        return (
            company_sim >= self.company_threshold and
            title_sim >= self.title_threshold
        )

    def calculate_info_richness(self, job: JobPosting) -> int:
        """공고의 정보 풍부도 점수 계산"""
        score = 0

        # 소스 우선순위
        source_priority = self.SOURCE_PRIORITY.get(
            JobSource(job.source) if isinstance(job.source, str) else job.source,
            0
        )
        score += source_priority

        # 기술 스택 정보
        if job.tech_stack:
            score += len(job.tech_stack) * 5

        # 요구사항/우대사항
        if job.requirements:
            score += len(job.requirements) * 3
        if job.preferred:
            score += len(job.preferred) * 2

        # 상세 설명
        if job.description:
            score += min(len(job.description) // 100, 20)

        # 위치 정보
        if job.location:
            score += 5

        # 급여 정보
        if job.salary:
            score += 10

        # 마감일 정보
        if job.deadline:
            score += 5

        return score

    def select_primary(self, jobs: List[JobPosting]) -> JobPosting:
        """중복 그룹에서 대표 공고 선택 (정보 풍부도 기준)"""
        if len(jobs) == 1:
            return jobs[0]

        # 정보 풍부도 점수로 정렬
        scored_jobs = [
            (job, self.calculate_info_richness(job))
            for job in jobs
        ]
        scored_jobs.sort(key=lambda x: x[1], reverse=True)

        return scored_jobs[0][0]

    def merge_job_info(
        self,
        primary: JobPosting,
        duplicates: List[JobPosting]
    ) -> JobPosting:
        """중복 공고들의 정보를 병합하여 대표 공고 보강"""
        # 기술 스택 병합
        all_tech = set(primary.tech_stack or [])
        for dup in duplicates:
            if dup.tech_stack:
                all_tech.update(dup.tech_stack)
        primary.tech_stack = list(all_tech) if all_tech else None

        # 요구사항 병합 (중복 제거)
        all_requirements = set(primary.requirements or [])
        for dup in duplicates:
            if dup.requirements:
                all_requirements.update(dup.requirements)
        primary.requirements = list(all_requirements) if all_requirements else None

        # 우대사항 병합
        all_preferred = set(primary.preferred or [])
        for dup in duplicates:
            if dup.preferred:
                all_preferred.update(dup.preferred)
        primary.preferred = list(all_preferred) if all_preferred else None

        # 누락된 정보 채우기
        if not primary.location:
            for dup in duplicates:
                if dup.location:
                    primary.location = dup.location
                    break

        if not primary.salary:
            for dup in duplicates:
                if dup.salary:
                    primary.salary = dup.salary
                    break

        if not primary.deadline and not primary.deadline_text:
            for dup in duplicates:
                if dup.deadline:
                    primary.deadline = dup.deadline
                    primary.deadline_text = dup.deadline_text
                    break

        if not primary.description or len(primary.description) < 100:
            for dup in duplicates:
                if dup.description and len(dup.description) > len(primary.description or ''):
                    primary.description = dup.description
                    break

        return primary

    def deduplicate(
        self,
        jobs: List[JobPosting],
        merge_info: bool = True,
    ) -> Tuple[List[JobPosting], List[DuplicateGroup]]:
        """
        공고 목록에서 중복 제거

        Args:
            jobs: 전체 공고 목록
            merge_info: 중복 공고 정보 병합 여부

        Returns:
            (중복 제거된 공고 목록, 중복 그룹 정보)
        """
        if not jobs:
            return [], []

        logger.info(f"[중복 탐지] {len(jobs)}개 공고 처리 시작")

        # 처리 상태 추적
        processed = [False] * len(jobs)
        unique_jobs: List[JobPosting] = []
        duplicate_groups: List[DuplicateGroup] = []

        for i, job1 in enumerate(jobs):
            if processed[i]:
                continue

            # 이 공고와 중복인 공고들 찾기
            duplicates = []
            similarity_scores = []

            for j, job2 in enumerate(jobs[i+1:], start=i+1):
                if processed[j]:
                    continue

                if self.is_duplicate(job1, job2):
                    company_sim, title_sim = self.calculate_similarity(job1, job2)
                    duplicates.append(job2)
                    similarity_scores.append((company_sim + title_sim) / 2)
                    processed[j] = True

            # 대표 공고 선택
            all_in_group = [job1] + duplicates
            primary = self.select_primary(all_in_group)

            # 정보 병합
            if merge_info and duplicates:
                others = [j for j in all_in_group if j != primary]
                primary = self.merge_job_info(primary, others)

            unique_jobs.append(primary)
            processed[i] = True

            # 중복 그룹 기록 (primary 제외)
            if duplicates:
                actual_duplicates = [j for j in all_in_group if j.id != primary.id]
                duplicate_groups.append(DuplicateGroup(
                    primary=primary,
                    duplicates=actual_duplicates,
                    similarity_scores=similarity_scores,
                ))

        # 통계 로깅
        total_duplicates = sum(len(g.duplicates) for g in duplicate_groups)
        logger.info(
            f"[중복 탐지] 완료: {len(jobs)}개 → {len(unique_jobs)}개 "
            f"(중복 {total_duplicates}개 제거, {len(duplicate_groups)}개 그룹)"
        )

        return unique_jobs, duplicate_groups

    def find_duplicates_for_job(
        self,
        target: JobPosting,
        jobs: List[JobPosting]
    ) -> List[Tuple[JobPosting, float]]:
        """특정 공고와 중복인 공고들 찾기"""
        duplicates = []

        for job in jobs:
            if job.id == target.id:
                continue

            if self.is_duplicate(target, job):
                company_sim, title_sim = self.calculate_similarity(target, job)
                avg_sim = (company_sim + title_sim) / 2
                duplicates.append((job, avg_sim))

        # 유사도 순 정렬
        duplicates.sort(key=lambda x: x[1], reverse=True)
        return duplicates
