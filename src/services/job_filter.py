"""
채용 공고 필터링 서비스

단일 책임: 채용 공고가 필터 조건에 맞는지 판별
"""
import re
from typing import List, Optional

from loguru import logger

from src.core.config import FilterConfig, get_config
from src.core.interfaces import FilterProtocol
from src.models import JobPosting


class JobFilter(FilterProtocol):
    """채용 공고 필터링 서비스

    설정된 키워드와 경력 조건에 따라 채용 공고를 필터링합니다.

    필터링 로직:
    1. 제외 키워드 체크 (타이틀에 포함 시 제외)
    2. 직무 키워드 체크 (OR 조건, 하나라도 매칭되면 포함)
    3. 경력 조건 체크 (신입 가능 공고만 포함)
    """

    def __init__(self, config: Optional[FilterConfig] = None):
        """
        Args:
            config: 필터 설정. None이면 기본 설정 사용.
        """
        self._config = config or get_config().filter

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
        """채용 공고가 필터 조건에 맞는지 확인

        Args:
            job: 확인할 채용 공고

        Returns:
            필터 조건 충족 여부
        """
        # 1. 제외 키워드 체크
        if self._contains_exclude_keyword(job.title):
            logger.debug(f"제외(키워드): {job.title}")
            return False

        # 2. 직무 키워드 체크
        if not self._matches_job_keyword(job):
            logger.debug(f"제외(직무불일치): {job.title}")
            return False

        # 3. 경력 조건 체크
        if not self._is_entry_level_friendly(job.experience_text):
            logger.debug(f"제외(경력): {job.title} - {job.experience_text}")
            return False

        return True

    def _contains_exclude_keyword(self, title: str) -> bool:
        """타이틀에 제외 키워드가 포함되어 있는지 확인"""
        title_lower = title.lower()
        return any(kw.lower() in title_lower for kw in self.exclude_keywords)

    def _matches_job_keyword(self, job: JobPosting) -> bool:
        """직무 키워드와 매칭되는지 확인 (OR 조건)"""
        search_text = f"{job.title} {job.description or ''}".lower()
        return any(kw.lower() in search_text for kw in self.job_keywords)

    def _is_entry_level_friendly(self, exp_text: Optional[str]) -> bool:
        """신입이 지원 가능한 공고인지 확인

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

        # 2. "경력 N년" 패턴 체크
        if self._requires_experience(exp_lower):
            return False

        # 3. "경력" 단어만 있고 신입 키워드 없으면 제외
        if self._is_experienced_only(exp_lower):
            return False

        return True

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
