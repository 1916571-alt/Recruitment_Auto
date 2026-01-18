"""
채용 공고 필터링 서비스

단일 책임: 채용 공고가 필터 조건에 맞는지 판별

v2.0: 스코어 기반 매칭 시스템
- must_have 키워드: 필수 (하나 이상 매칭 필요)
- good_to_have 키워드: 추가 점수
- exclude 키워드: 즉시 제외
"""
import re
from typing import List, Optional, Tuple, Dict

from loguru import logger

from src.core.config import (
    FilterConfig,
    get_config,
    JOB_CATEGORY_KEYWORDS,
    SCORE_CONFIG
)
from src.core.interfaces import FilterProtocol
from src.models import JobPosting


class JobFilter(FilterProtocol):
    """채용 공고 필터링 서비스 (v2.0 - 스코어 기반)

    설정된 키워드와 경력 조건에 따라 채용 공고를 필터링합니다.

    필터링 로직:
    1. 전역 제외 키워드 체크 (타이틀에 포함 시 제외)
    2. 스코어 기반 직무 매칭 (카테고리별 점수 계산)
    3. 경력 조건 체크 (신입 가능 공고만 포함)
    """

    def __init__(self, config: Optional[FilterConfig] = None):
        """
        Args:
            config: 필터 설정. None이면 기본 설정 사용.
        """
        self._config = config or get_config().filter
        self._category_keywords = JOB_CATEGORY_KEYWORDS
        self._score_config = SCORE_CONFIG

    @property
    def job_keywords(self) -> List[str]:
        """포함할 직무 키워드"""
        return self._config.job_keywords

    @property
    def exclude_keywords(self) -> List[str]:
        """제외할 키워드"""
        return self._config.exclude_keywords

    @property
    def entry_level_keywords(self) -> List[str]:
        """신입 가능 키워드"""
        return self._config.entry_level_keywords

    def matches(self, job: JobPosting) -> bool:
        """채용 공고가 필터 조건에 맞는지 확인 (v2.0 스코어 기반)

        Args:
            job: 확인할 채용 공고

        Returns:
            필터 조건 충족 여부
        """
        # 1. 전역 제외 키워드 체크
        if self._contains_exclude_keyword(job.title):
            logger.debug(f"제외(전역키워드): {job.title}")
            return False

        # 2. 스코어 기반 직무 매칭
        best_category, best_score = self.calculate_best_category(job)
        if best_score < self._score_config["threshold"]:
            logger.debug(f"제외(스코어부족): {job.title} - 최고점수: {best_score}")
            return False

        # 3. 경력 조건 체크
        if not self._is_entry_level_friendly(job.experience_text):
            logger.debug(f"제외(경력): {job.title} - {job.experience_text}")
            return False

        logger.debug(f"통과: {job.title} - 카테고리: {best_category}, 점수: {best_score}")
        return True

    def matches_with_category(self, job: JobPosting) -> Tuple[bool, Optional[str], float]:
        """채용 공고 필터링 + 카테고리 분류 동시 수행

        Args:
            job: 확인할 채용 공고

        Returns:
            (통과 여부, 카테고리, 점수)
        """
        # 1. 전역 제외 키워드 체크
        if self._contains_exclude_keyword(job.title):
            return False, None, 0.0

        # 2. 스코어 기반 직무 매칭
        best_category, best_score = self.calculate_best_category(job)
        if best_score < self._score_config["threshold"]:
            return False, None, best_score

        # 3. 경력 조건 체크
        if not self._is_entry_level_friendly(job.experience_text):
            return False, None, 0.0

        return True, best_category, best_score

    def calculate_best_category(self, job: JobPosting) -> Tuple[Optional[str], float]:
        """모든 카테고리에 대해 점수를 계산하고 최고 점수 카테고리 반환

        Args:
            job: 채용 공고

        Returns:
            (최고 점수 카테고리, 점수)
        """
        best_category = None
        best_score = 0.0

        for category, keywords in self._category_keywords.items():
            score = self.calculate_category_score(job, category)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category, best_score

    def calculate_category_score(self, job: JobPosting, category: str) -> float:
        """특정 카테고리에 대한 점수 계산

        Args:
            job: 채용 공고
            category: 카테고리 이름 (data, backend, frontend, pm, sales, procurement)

        Returns:
            점수 (음수면 제외 대상)
        """
        if category not in self._category_keywords:
            return 0.0

        keywords = self._category_keywords[category]
        search_text = f"{job.title} {job.description or ''}".lower()

        # 1. exclude 키워드 체크 - 하나라도 있으면 이 카테고리 점수 0
        exclude_keywords = keywords.get("exclude", [])
        for kw in exclude_keywords:
            if kw.lower() in search_text:
                return 0.0

        score = 0.0
        has_must_have = False

        # 2. must_have 키워드 체크
        must_have_keywords = keywords.get("must_have", [])
        for kw in must_have_keywords:
            if kw.lower() in search_text:
                score += self._score_config["must_have_score"]
                has_must_have = True
                break  # 하나만 매칭되면 충분

        # must_have가 없으면 이 카테고리 점수 0
        if not has_must_have:
            return 0.0

        # 3. good_to_have 키워드 체크
        good_to_have_keywords = keywords.get("good_to_have", [])
        matched_good = 0
        for kw in good_to_have_keywords:
            if kw.lower() in search_text:
                score += self._score_config["good_to_have_score"]
                matched_good += 1
                if matched_good >= 3:  # 최대 3개까지만 점수 부여
                    break

        return score

    def _contains_exclude_keyword(self, title: str) -> bool:
        """타이틀에 전역 제외 키워드가 포함되어 있는지 확인"""
        title_lower = title.lower()
        return any(kw.lower() in title_lower for kw in self.exclude_keywords)

    def _matches_job_keyword(self, job: JobPosting) -> bool:
        """직무 키워드와 매칭되는지 확인 (레거시 호환용)"""
        search_text = f"{job.title} {job.description or ''}".lower()
        return any(kw.lower() in search_text for kw in self.job_keywords)

    def _is_entry_level_friendly(self, exp_text: Optional[str]) -> bool:
        """신입이 지원 가능한 공고인지 확인 (v2.0 - 우대 vs 필수 구분)

        Args:
            exp_text: 경력 요건 텍스트

        Returns:
            신입 지원 가능 여부
        """
        if not exp_text:
            return True

        exp_lower = exp_text.lower().strip()

        # 1. 신입 가능 키워드가 있으면 포함
        if self._has_entry_keyword(exp_lower):
            return True

        # 2. "우대" 키워드가 있고 "필수"가 없으면 신입 가능
        # 예: "경력 3년 이상 우대" → 신입 가능
        if self._is_experience_preferred_not_required(exp_lower):
            return True

        # 3. "경력 N년" 패턴 체크 (필수인 경우)
        if self._requires_experience(exp_lower):
            return False

        # 4. "경력" 단어만 있고 신입 키워드 없으면 제외
        if self._is_experienced_only(exp_lower):
            return False

        return True

    def _is_experience_preferred_not_required(self, text: str) -> bool:
        """경력이 우대사항이고 필수가 아닌지 확인

        예시:
        - "경력 3년 이상 우대" → True (신입 가능)
        - "경력 3년 필수" → False (신입 불가)
        - "경력 우대" → True (신입 가능)
        """
        preferred_keywords = ["우대", "preferr", "plus", "환영"]
        required_keywords = ["필수", "require", "must", "필요"]

        has_preferred = any(kw in text for kw in preferred_keywords)
        has_required = any(kw in text for kw in required_keywords)

        # 우대는 있고 필수는 없는 경우
        if has_preferred and not has_required:
            return True

        return False

    def _has_entry_keyword(self, text: str) -> bool:
        """신입 가능 키워드 포함 여부"""
        return any(kw.lower() in text for kw in self.entry_level_keywords)

    def _requires_experience(self, text: str) -> bool:
        """경력 요구사항 체크

        다음 패턴을 감지합니다:
        - "경력 1년", "경력1년", "경력2년↑"
        - "1년 이상", "2년 이상"
        - "1~3년", "1-3년"
        - "경력 1~3", "경력 1-3"
        """
        career_patterns = [
            r"경력\s*(\d+)\s*년?\s*[↑이상]?",
            r"(\d+)\s*년\s*이상",
            r"(\d+)\s*~\s*(\d+)\s*년",
            r"(\d+)\s*-\s*(\d+)\s*년",
            r"(\d+)\s*년\s*[~↑]",
            r"경력\s*(\d+)\s*[~\-]\s*(\d+)",
        ]

        for pattern in career_patterns:
            match = re.search(pattern, text)
            if match:
                years = [int(g) for g in match.groups() if g and g.isdigit()]
                if years and min(years) >= 1:
                    return True

        return False

    def _is_experienced_only(self, text: str) -> bool:
        """경력직만 요구하는지 확인"""
        return "경력" in text and not any(kw in text for kw in ["신입", "무관"])

    def filter_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """채용 공고 리스트 필터링

        Args:
            jobs: 필터링할 채용 공고 리스트

        Returns:
            필터 조건에 맞는 공고 리스트
        """
        filtered = [job for job in jobs if self.matches(job)]
        logger.info(f"필터링 완료: {len(jobs)}건 → {len(filtered)}건")
        return filtered
