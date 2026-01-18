"""
채용 공고 수집 서비스

단일 책임: 여러 크롤러를 조율하여 채용 공고 수집
"""
from typing import List, Optional

from loguru import logger

from src.core.config import CrawlerConfig, get_config
from src.core.interfaces import CrawlerProtocol, FilterProtocol
from src.models import JobPosting
from src.services.deduplication import JobDeduplicator


class JobCollector:
    """채용 공고 수집 서비스

    여러 크롤러를 실행하고 결과를 통합하는 역할을 담당합니다.
    의존성 주입을 통해 크롤러와 필터를 받습니다.
    Fuzzy Matching 기반 중복 탐지를 지원합니다.
    """

    def __init__(
        self,
        crawlers: List[CrawlerProtocol],
        job_filter: Optional[FilterProtocol] = None,
        config: Optional[CrawlerConfig] = None,
        deduplicator: Optional[JobDeduplicator] = None,
    ):
        """
        Args:
            crawlers: 실행할 크롤러 리스트
            job_filter: 필터링에 사용할 필터 (없으면 필터링 안 함)
            config: 크롤러 설정
            deduplicator: 중복 탐지기 (없으면 기본 중복 탐지 사용)
        """
        self._crawlers = crawlers
        self._filter = job_filter
        self._config = config or get_config().crawler
        self._deduplicator = deduplicator or JobDeduplicator()

    async def collect(self, fetch_details: bool = False) -> List[JobPosting]:
        """모든 크롤러에서 채용 공고 수집

        Args:
            fetch_details: 상세 정보 수집 여부

        Returns:
            수집된 채용 공고 리스트 (중복 제거됨)
        """
        all_jobs: List[JobPosting] = []

        for crawler in self._crawlers:
            try:
                jobs = await self._run_crawler(crawler)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"크롤러 오류 ({crawler.source_name}): {e}")
                continue

        # 중복 제거
        unique_jobs = self._deduplicate(all_jobs)

        # 필터링
        if self._filter:
            unique_jobs = [j for j in unique_jobs if self._filter.matches(j)]

        logger.info(f"수집 완료: 총 {len(unique_jobs)}건")

        # 상세 정보 수집
        if fetch_details and unique_jobs:
            await self._fetch_details(unique_jobs)

        return unique_jobs

    async def _run_crawler(self, crawler: CrawlerProtocol) -> List[JobPosting]:
        """단일 크롤러 실행

        Args:
            crawler: 실행할 크롤러

        Returns:
            수집된 채용 공고 리스트
        """
        logger.info(f"[{crawler.source_name}] 크롤링 시작...")

        # 컨텍스트 매니저 지원 여부 확인
        if hasattr(crawler, "__aenter__"):
            async with crawler:
                jobs = await crawler.crawl()
        else:
            jobs = await crawler.crawl()

        logger.info(f"[{crawler.source_name}] {len(jobs)}건 수집")
        return jobs

    async def _fetch_details(self, jobs: List[JobPosting]) -> None:
        """상세 정보 수집

        Args:
            jobs: 상세 정보를 수집할 공고 리스트
        """
        max_fetch = self._config.max_detail_fetch
        to_fetch = jobs[:max_fetch]

        logger.info(f"상세 정보 수집: {len(to_fetch)}건")

        for job in to_fetch:
            try:
                crawler = self._find_crawler_for_job(job)
                if crawler:
                    if hasattr(crawler, "__aenter__"):
                        async with crawler:
                            await crawler.get_job_detail(job)
                    else:
                        await crawler.get_job_detail(job)
            except Exception as e:
                logger.debug(f"상세 정보 오류 ({job.id}): {e}")

    def _find_crawler_for_job(self, job: JobPosting) -> Optional[CrawlerProtocol]:
        """채용 공고에 맞는 크롤러 찾기"""
        for crawler in self._crawlers:
            if crawler.source_name == job.source.value:
                return crawler
        return None

    def _deduplicate(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """Fuzzy Matching 기반 중복 제거

        동일 소스 내 중복은 source_id로 빠르게 제거하고,
        크로스 소스 중복은 Fuzzy Matching으로 탐지합니다.

        Args:
            jobs: 중복이 있을 수 있는 공고 리스트

        Returns:
            중복이 제거된 공고 리스트
        """
        # 1단계: 같은 소스 내 중복 빠르게 제거
        seen_keys = set()
        stage1_unique = []
        for job in jobs:
            key = f"{job.source}_{job.source_id or job.id}"
            if key not in seen_keys:
                seen_keys.add(key)
                stage1_unique.append(job)

        if len(jobs) != len(stage1_unique):
            logger.debug(f"1단계 중복 제거 (같은 소스): {len(jobs)}건 → {len(stage1_unique)}건")

        # 2단계: 크로스 소스 중복 Fuzzy Matching으로 탐지
        unique_jobs, duplicate_groups = self._deduplicator.deduplicate(
            stage1_unique,
            merge_info=True,  # 정보 병합 활성화
        )

        # 중복 그룹 로깅
        if duplicate_groups:
            for group in duplicate_groups[:5]:  # 최대 5개만 로깅
                sources = [group.primary.source]
                sources.extend([d.source for d in group.duplicates])
                source_str = ", ".join(str(s) for s in set(sources))
                logger.debug(
                    f"중복 발견: '{group.primary.company_name}' - '{group.primary.title[:30]}...' "
                    f"(소스: {source_str}, 중복 {len(group.duplicates)}건)"
                )

        return unique_jobs
