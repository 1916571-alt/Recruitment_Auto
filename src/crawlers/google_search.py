"""
Google Custom Search API 크롤러

환경변수:
    GOOGLE_API_KEY: Google API 키
    GOOGLE_CSE_ID: Custom Search Engine ID

설정:
    config/settings.py의 GOOGLE_SEARCH_QUERIES, ACTIVE_JOB_TYPES 참조
"""
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode

from loguru import logger

from src.core.config import get_config
from src.core.interfaces import FilterProtocol, HttpClientProtocol
from src.models import JobPosting, JobSource, ExperienceLevel
from config.settings import GOOGLE_SEARCH_QUERIES, ACTIVE_JOB_TYPES

from .base import BaseCrawler


class GoogleSearchCrawler(BaseCrawler):
    """Google Custom Search API 크롤러

    Google CSE를 통해 채용 사이트 검색 결과를 수집합니다.
    무료 티어: 하루 100회 검색

    검색 쿼리는 config/settings.py에서 직군별로 관리합니다.
    """

    source = JobSource.GOOGLE_SEARCH
    API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        http_client: Optional[HttpClientProtocol] = None,
        job_filter: Optional[FilterProtocol] = None,
        job_types: Optional[List[str]] = None,
    ):
        """
        Args:
            http_client: HTTP 클라이언트
            job_filter: 채용 공고 필터
            job_types: 검색할 직군 목록 (None이면 ACTIVE_JOB_TYPES 사용)
        """
        super().__init__(http_client, job_filter)
        config = get_config()
        self._api_key = config.google_api_key
        self._cse_id = config.google_cse_id
        self._job_types = job_types or ACTIVE_JOB_TYPES

    def _get_search_queries(self) -> List[str]:
        """활성화된 직군의 검색 쿼리 목록 반환"""
        queries = []
        for job_type in self._job_types:
            if job_type in GOOGLE_SEARCH_QUERIES:
                queries.extend(GOOGLE_SEARCH_QUERIES[job_type])
            else:
                logger.warning(f"[Google] 알 수 없는 직군: {job_type}")
        return queries

    def _validate_config(self) -> bool:
        """API 설정 유효성 검사"""
        if not self._api_key:
            logger.warning("[Google] GOOGLE_API_KEY 환경변수가 설정되지 않음")
            return False
        if not self._cse_id:
            logger.warning("[Google] GOOGLE_CSE_ID 환경변수가 설정되지 않음")
            return False
        return True

    async def crawl(self) -> List[JobPosting]:
        """채용 공고 검색

        Returns:
            수집된 채용 공고 리스트
        """
        if not self._validate_config():
            logger.warning("[Google] API 설정 없음, 크롤링 건너뜀")
            return []

        all_jobs: List[JobPosting] = []
        search_queries = self._get_search_queries()
        logger.info(f"[Google] {len(search_queries)}개 쿼리로 검색 시작 (직군: {self._job_types})")

        for query in search_queries:
            try:
                jobs = await self._search(query)
                all_jobs.extend(jobs)
                logger.info(f"[Google] '{query}' 검색: {len(jobs)}건")
            except Exception as e:
                logger.error(f"[Google] '{query}' 검색 오류: {e}")
                continue

        # 중복 제거 및 필터링
        unique_jobs = self._deduplicate_and_filter(all_jobs)
        logger.info(f"[Google] 총 {len(unique_jobs)}건 수집 완료")
        return unique_jobs

    async def _search(
        self,
        query: str,
        start: int = 1,
        num: int = 10,
    ) -> List[JobPosting]:
        """단일 검색 쿼리 실행

        Args:
            query: 검색어
            start: 시작 위치 (1-based, 최대 100)
            num: 결과 개수 (1-10)

        Returns:
            검색 결과에서 파싱된 채용 공고 리스트
        """
        params = {
            "key": self._api_key,
            "cx": self._cse_id,
            "q": query,
            "start": start,
            "num": min(num, 10),  # 최대 10개
            "lr": "lang_ko",  # 한국어
            "dateRestrict": "m1",  # 최근 1개월
        }

        url = f"{self.API_ENDPOINT}?{urlencode(params)}"
        response = await self.fetch_json(url)

        if not response:
            logger.warning(f"[Google] API 응답 없음: {query}")
            return []

        # API 오류 확인
        if "error" in response:
            error = response["error"]
            logger.error(f"[Google] API 오류: {error.get('message', 'Unknown')}")
            return []

        items = response.get("items", [])
        return self._parse_search_results(items)

    def _parse_search_results(self, items: List[dict]) -> List[JobPosting]:
        """검색 결과 파싱

        Args:
            items: Google API 검색 결과 아이템 목록

        Returns:
            파싱된 채용 공고 리스트
        """
        jobs: List[JobPosting] = []

        for item in items:
            try:
                job = self._parse_search_item(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.error(f"[Google] 파싱 오류: {e}")
                continue

        return jobs

    def _parse_search_item(self, item: dict) -> Optional[JobPosting]:
        """개별 검색 결과 파싱

        Google CSE 응답 구조:
        {
            "title": "포지션명 - 회사명 | 사이트",
            "link": "https://...",
            "snippet": "설명...",
        }

        Args:
            item: 검색 결과 아이템

        Returns:
            파싱된 JobPosting 또는 None
        """
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")

        if not link:
            return None

        # 제목에서 회사명, 포지션 추출
        company_name, position = self._extract_company_and_title(title, link)

        if not position:
            position = title

        # 회사명을 찾지 못했으면 URL에서 추출 시도
        if not company_name:
            company_name = self._extract_company_from_url(link)

        if not company_name:
            company_name = "Unknown"

        # 경력 수준 추출
        combined_text = f"{title} {snippet}"
        experience_level = self._determine_experience_level(combined_text)
        experience_text = self._extract_experience_text(combined_text)

        return JobPosting(
            id=self.generate_id(self.source.value, link),
            title=position,
            company_name=company_name,
            experience_level=experience_level,
            experience_text=experience_text,
            description=snippet[:500] if snippet else None,
            source=self.source,
            source_url=link,
            source_id=link,
            crawled_at=datetime.now(),
        )

    def _extract_company_and_title(
        self,
        title: str,
        url: str = "",
    ) -> tuple[str, str]:
        """제목에서 회사명과 포지션 분리

        다양한 패턴 지원:
        - "데이터 분석가 - 네이버 | Wanted"
        - "[네이버] 데이터 분석가 채용"
        - "네이버 채용: 데이터 분석가"
        - "데이터 분석가 | 네이버"

        Args:
            title: 검색 결과 제목
            url: 원본 URL (힌트용)

        Returns:
            (회사명, 포지션) 튜플
        """
        # 사이트명 제거 (예: " | Wanted", " | 잡코리아")
        site_patterns = [
            r"\s*\|\s*(Wanted|wanted|원티드)",
            r"\s*\|\s*(JobKorea|잡코리아)",
            r"\s*\|\s*(사람인|Saramin)",
            r"\s*\|\s*(프로그래머스|Programmers)",
            r"\s*-\s*(Wanted|wanted|원티드)$",
            r"\s*-\s*(채용|careers?)$",
        ]
        cleaned_title = title
        for pattern in site_patterns:
            cleaned_title = re.sub(pattern, "", cleaned_title, flags=re.IGNORECASE)

        # [회사명] 패턴
        match = re.match(r"\[(.+?)\]\s*(.+)", cleaned_title)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # "회사명 | 포지션" 패턴
        if " | " in cleaned_title:
            parts = cleaned_title.split(" | ")
            if len(parts) >= 2:
                # 첫 부분이 회사명인지 포지션인지 판별
                first, second = parts[0].strip(), parts[1].strip()
                if self._looks_like_company(first):
                    return first, second
                else:
                    return second, first

        # "포지션 - 회사명" 패턴
        separators = [" - ", " – ", " — "]
        for sep in separators:
            if sep in cleaned_title:
                parts = cleaned_title.split(sep)
                if len(parts) >= 2:
                    # 마지막 부분이 보통 회사명
                    position_part = sep.join(parts[:-1]).strip()
                    company_part = parts[-1].strip()
                    return company_part, position_part

        # "회사명 채용: 포지션" 패턴
        match = re.match(r"(.+?)\s*채용\s*[:：]\s*(.+)", cleaned_title)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        return "", cleaned_title

    def _looks_like_company(self, text: str) -> bool:
        """텍스트가 회사명처럼 보이는지 판별"""
        company_indicators = [
            "(주)", "㈜", "주식회사", "Corp", "Inc", "Ltd",
            "컴퍼니", "Company", "그룹", "Group",
        ]
        return any(ind in text for ind in company_indicators)

    def _extract_company_from_url(self, url: str) -> str:
        """URL에서 회사명 추출 시도

        wanted.co.kr/wd/12345 -> ""
        careers.kakao.com/... -> "카카오"
        """
        url_lower = url.lower()

        # 알려진 회사 도메인 매핑
        domain_company_map = {
            "careers.kakao.com": "카카오",
            "careers.kakaocorp.com": "카카오",
            "recruit.navercorp.com": "네이버",
            "careers.linecorp.com": "라인",
            "careers.toss.im": "토스",
            "careers.woowahan.com": "우아한형제들",
            "recruit.coupang.com": "쿠팡",
        }

        for domain, company in domain_company_map.items():
            if domain in url_lower:
                return company

        return ""

    def _determine_experience_level(self, text: str) -> ExperienceLevel:
        """경력 레벨 결정

        Args:
            text: 분석할 텍스트

        Returns:
            ExperienceLevel enum 값
        """
        text_lower = text.lower()

        if "인턴" in text_lower or "intern" in text_lower:
            return ExperienceLevel.INTERN

        if "경력무관" in text_lower or "경력 무관" in text_lower:
            return ExperienceLevel.ANY

        if "신입" in text_lower or "entry" in text_lower:
            return ExperienceLevel.ENTRY

        if "주니어" in text_lower or "junior" in text_lower:
            return ExperienceLevel.JUNIOR

        # 경력 N년 패턴
        if re.search(r"경력\s*\d+\s*년", text_lower):
            return ExperienceLevel.EXPERIENCED

        # 기본값: 경력무관으로 설정 (검색 쿼리에 신입/경력무관 포함)
        return ExperienceLevel.ANY

    def _extract_experience_text(self, text: str) -> Optional[str]:
        """경력 요건 원문 추출"""
        patterns = [
            r"(신입|경력무관|경력\s*무관)",
            r"(경력\s*\d+\s*년\s*이상)",
            r"(인턴|주니어|junior)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _deduplicate_and_filter(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """중복 제거 및 필터링

        Args:
            jobs: 전체 채용 공고 리스트

        Returns:
            중복 제거 및 필터링된 리스트
        """
        seen_urls = set()
        unique_jobs = []

        for job in jobs:
            # URL 기반 중복 제거
            if job.source_url in seen_urls:
                continue
            seen_urls.add(job.source_url)

            # 필터 적용
            if self.matches_filter(job):
                unique_jobs.append(job)

        return unique_jobs

    async def get_job_detail(self, job: JobPosting) -> JobPosting:
        """상세 정보 가져오기

        Google 검색 결과는 snippet만 제공하므로,
        필요시 원본 페이지를 크롤링해야 함.
        현재는 기본 정보만 반환.

        Args:
            job: 기본 정보가 담긴 채용 공고

        Returns:
            (현재는) 입력과 동일한 채용 공고
        """
        # TODO: 원본 페이지 크롤링 구현 (사이트별 파서 필요)
        return job
